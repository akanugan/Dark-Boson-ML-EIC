#include "DarkBosonKinematics.h"

#include <TFoam.h>
#include <TFoamIntegrand.h>
#include <TFile.h>
#include <TH1D.h>
#include <TH2D.h>
#include <TMath.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TRandom3.h>
#include <TTree.h>
#include <TVector3.h>

#include <boost/multiprecision/cpp_dec_float.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr double kElectronMass = 0.00051099895000;
constexpr double kAlpha = 1.0 / 137.035999084;
const double kElectricCharge = std::sqrt(4.0 * TMath::Pi() * kAlpha);
constexpr double kGeV2ToPb = 3.893793721e8;
constexpr double kFmToGeVInv = 5.067730716;

double lambda(double x, double y, double z) {
  return x * x + y * y + z * z - 2.0 * x * y - 2.0 * x * z -
         2.0 * y * z;
}

double pcm(double parent_mass, double mass1, double mass2) {
  const double radicand = lambda(parent_mass * parent_mass, mass1 * mass1,
                                  mass2 * mass2);
  if (radicand <= 0.0) return 0.0;
  return std::sqrt(radicand) / (2.0 * parent_mass);
}

double ecm(double parent_mass, double mass1, double mass2) {
  return (parent_mass * parent_mass + mass1 * mass1 - mass2 * mass2) /
         (2.0 * parent_mass);
}

double helm_form_factor(double t, int mass_number) {
  if (!(t >= 0.0) || !std::isfinite(t)) return 0.0;
  const double q = std::sqrt(t);
  const double radius = 1.1 * std::cbrt(static_cast<double>(mass_number)) *
                        kFmToGeVInv;
  const double skin = 0.9 * kFmToGeVInv;
  const double x = q * radius;

  double three_j1_over_x = 1.0;
  if (std::abs(x) > 1.0e-4) {
    const double j1 = std::sin(x) / (x * x) - std::cos(x) / x;
    three_j1_over_x = 3.0 * j1 / x;
  } else {
    const double x2 = x * x;
    three_j1_over_x = 1.0 - x2 / 10.0 + x2 * x2 / 280.0;
  }
  return three_j1_over_x * std::exp(-0.5 * q * q * skin * skin);
}

struct GeneratorConfig {
  double mass = 1.0;
  double cut_mass = -1.0;
  double coupling = 1.0e-4;
  double electron_energy = 18.0;
  double ion_energy_per_nucleon = 100.0;
  double ion_mass = 183.0;
  int mass_number = 197;
  int charge_number = 79;
  long long events = 20000;
  int cells = 500;
  int samples = 200;
  int bins = 8;
  unsigned long seed = 250508871;
  std::string output = "data/root/vector_m1.root";
  bool integrate_paper_cut = false;
  bool quiet = false;
};

double selection_mass(const GeneratorConfig& cfg) {
  return cfg.cut_mass > 0.0 ? cfg.cut_mass : cfg.mass;
}

using HighPrecision = boost::multiprecision::cpp_dec_float_50;

HighPrecision hp_lambda(const HighPrecision& x, const HighPrecision& y,
                        const HighPrecision& z) {
  return x * x + y * y + z * z - 2 * x * y - 2 * x * z - 2 * y * z;
}

HighPrecision hp_pcm(const HighPrecision& parent_mass,
                     const HighPrecision& mass1,
                     const HighPrecision& mass2) {
  return sqrt(hp_lambda(parent_mass * parent_mass, mass1 * mass1,
                        mass2 * mass2)) /
         (2 * parent_mass);
}

HighPrecision hp_ecm(const HighPrecision& parent_mass,
                     const HighPrecision& mass1,
                     const HighPrecision& mass2) {
  return (parent_mass * parent_mass + mass1 * mass1 - mass2 * mass2) /
         (2 * parent_mass);
}

class VectorBosonDensity final : public TFoamIntegrand {
 public:
  explicit VectorBosonDensity(const GeneratorConfig& config) : cfg_(config) {
    const double ion_energy = cfg_.mass_number * cfg_.ion_energy_per_nucleon;
    const double electron_p =
        std::sqrt(cfg_.electron_energy * cfg_.electron_energy -
                  kElectronMass * kElectronMass);
    const double ion_p =
        std::sqrt(ion_energy * ion_energy - cfg_.ion_mass * cfg_.ion_mass);

    electron_in_lab_.SetPxPyPzE(0.0, 0.0, -electron_p,
                                cfg_.electron_energy);
    ion_in_lab_.SetPxPyPzE(0.0, 0.0, ion_p, ion_energy);
    total_lab_ = electron_in_lab_ + ion_in_lab_;
    sqrt_s_ = total_lab_.M();
    s_ = total_lab_.M2();
    cm_to_lab_beta_ = total_lab_.BoostVector();

    p_initial_cm_ = pcm(sqrt_s_, cfg_.ion_mass, kElectronMass);
    ion_initial_cm_.SetPxPyPzE(
        0.0, 0.0, p_initial_cm_,
        ecm(sqrt_s_, cfg_.ion_mass, kElectronMass));
    electron_initial_cm_.SetPxPyPzE(
        0.0, 0.0, -p_initial_cm_,
        ecm(sqrt_s_, kElectronMass, cfg_.ion_mass));

    calculate_global_t_bounds();
    if (!(t_min_ > 0.0 && t_max_ > t_min_)) {
      throw std::runtime_error("Invalid phase-space t boundaries");
    }
  }

  Double_t Density(Int_t dimensions, Double_t* x) override {
    if (dimensions != 4) return 0.0;
    darkboson::EventKinematics event;
    double density_pb = 0.0;
    if (!build_event(x, event, density_pb)) return 0.0;
    return density_pb;
  }

  bool build_event(const double* x, darkboson::EventKinematics& event,
                   double& density_pb) const {
    const double log_ratio = std::log(t_max_ / t_min_);
    const double t = t_min_ * std::exp(log_ratio * x[0]);
    const double jacobian_t = t * log_ratio;

    const double min_pair_mass = kElectronMass + cfg_.mass;
    const double max_pair_mass = pair_mass_max(t);
    if (!(max_pair_mass > min_pair_mass) || !std::isfinite(max_pair_mass)) {
      return false;
    }

    const double pair_mass =
        min_pair_mass + x[1] * (max_pair_mass - min_pair_mass);
    const double jacobian_pair_mass = max_pair_mass - min_pair_mass;
    const double cos_decay = 2.0 * x[2] - 1.0;
    const double sin_decay =
        std::sqrt(std::max(0.0, 1.0 - cos_decay * cos_decay));
    const double decay_phi = 2.0 * TMath::Pi() * x[3];
    const double angular_jacobian = 4.0 * TMath::Pi();

    const HighPrecision h_root_s(sqrt_s_);
    const HighPrecision h_ion(cfg_.ion_mass);
    const HighPrecision h_electron(kElectronMass);
    const HighPrecision h_pair(pair_mass);
    const HighPrecision h_initial_e = hp_ecm(h_root_s, h_ion, h_electron);
    const HighPrecision h_initial_p = hp_pcm(h_root_s, h_ion, h_electron);
    const HighPrecision h_outgoing_e = hp_ecm(h_root_s, h_ion, h_pair);
    const HighPrecision h_outgoing_p = hp_pcm(h_root_s, h_ion, h_pair);
    const HighPrecision h_forward_t =
        2 * (h_initial_e * h_outgoing_e - h_initial_p * h_outgoing_p -
             h_ion * h_ion);
    HighPrecision h_one_minus_cos =
        (HighPrecision(t) - h_forward_t) /
        (2 * h_initial_p * h_outgoing_p);
    const HighPrecision h_tolerance("1e-30");
    if (h_one_minus_cos < -h_tolerance || h_one_minus_cos > 2 + h_tolerance) {
      return false;
    }
    if (h_one_minus_cos < 0) h_one_minus_cos = 0;
    if (h_one_minus_cos > 2) h_one_minus_cos = 2;
    const double one_minus_cos = h_one_minus_cos.convert_to<double>();
    const double outgoing_ion_p = h_outgoing_p.convert_to<double>();
    const double outgoing_ion_e = h_outgoing_e.convert_to<double>();
    if (!(outgoing_ion_p > 0.0)) return false;
    const double cos_ion = 1.0 - one_minus_cos;
    const double sin_ion =
        std::sqrt(std::max(0.0, one_minus_cos * (2.0 - one_minus_cos)));

    TLorentzVector ion_out_cm(outgoing_ion_p * sin_ion, 0.0,
                              outgoing_ion_p * cos_ion, outgoing_ion_e);
    const TLorentzVector pair_cm =
        electron_initial_cm_ + ion_initial_cm_ - ion_out_cm;

    const double decay_p = pcm(pair_mass, cfg_.mass, kElectronMass);
    if (!(decay_p >= 0.0)) return false;
    TLorentzVector boson_pair_rest(
        decay_p * sin_decay * std::cos(decay_phi),
        decay_p * sin_decay * std::sin(decay_phi), decay_p * cos_decay,
        ecm(pair_mass, cfg_.mass, kElectronMass));
    TLorentzVector electron_out_pair_rest(
        -boson_pair_rest.Px(), -boson_pair_rest.Py(), -boson_pair_rest.Pz(),
        ecm(pair_mass, kElectronMass, cfg_.mass));

    const TVector3 pair_boost = pair_cm.BoostVector();
    TLorentzVector boson_cm = boson_pair_rest;
    TLorentzVector electron_out_cm = electron_out_pair_rest;
    boson_cm.Boost(pair_boost);
    electron_out_cm.Boost(pair_boost);

    const TLorentzVector nuclear_sum = ion_initial_cm_ + ion_out_cm;
    const double s_tilde =
        (electron_out_cm + boson_cm).M2() -
        kElectronMass * kElectronMass;
    const double u_tilde =
        (electron_initial_cm_ - boson_cm).M2() -
        kElectronMass * kElectronMass;
    const double t2 =
        (electron_out_cm - electron_initial_cm_).M2();
    const double st_plus_ut = s_tilde + u_tilde;
    const double st_ut = s_tilde * u_tilde;
    if (std::abs(st_ut) < 1.0e-30 || std::abs(st_plus_ut) < 1.0e-30) {
      return false;
    }

    const double p_dot_in = nuclear_sum.Dot(electron_initial_cm_);
    const double p_dot_out = nuclear_sum.Dot(electron_out_cm);
    const double nuclear_sum2 = nuclear_sum.M2();
    const double ratio =
        (u_tilde * p_dot_in + s_tilde * p_dot_out) / st_plus_ut;

    const double reduced_amplitude =
        2.0 * (s_tilde * s_tilde + u_tilde * u_tilde) / st_ut *
            nuclear_sum2 -
        8.0 * t / st_ut *
            (p_dot_in * p_dot_in + p_dot_out * p_dot_out +
             0.5 * (t2 + cfg_.mass * cfg_.mass) * nuclear_sum2) +
        2.0 * st_plus_ut * st_plus_ut /
            (s_tilde * s_tilde * u_tilde * u_tilde) *
            (cfg_.mass * cfg_.mass +
             2.0 * kElectronMass * kElectronMass) *
            (nuclear_sum2 * t - 4.0 * ratio * ratio);

    if (!std::isfinite(reduced_amplitude) || reduced_amplitude <= 0.0) {
      return false;
    }

    const double form_factor = helm_form_factor(t, cfg_.mass_number);
    const double coupling_factor =
        std::pow(kElectricCharge, 4) * cfg_.coupling * cfg_.coupling *
        cfg_.charge_number * cfg_.charge_number;
    const double denominator =
        std::pow(2.0 * TMath::Pi(), 4) * 64.0 *
        p_initial_cm_ * p_initial_cm_ * s_;
    const double differential_gev =
        coupling_factor * decay_p / denominator *
        std::pow(form_factor / t, 2) * reduced_amplitude;
    const double jacobian =
        jacobian_t * jacobian_pair_mass * angular_jacobian;
    density_pb = differential_gev * jacobian * kGeV2ToPb;
    if (!(density_pb >= 0.0) || !std::isfinite(density_pb)) return false;

    TLorentzVector ion_out_lab = ion_out_cm;
    TLorentzVector electron_out_lab = electron_out_cm;
    TLorentzVector boson_lab = boson_cm;
    ion_out_lab.Boost(cm_to_lab_beta_);
    electron_out_lab.Boost(cm_to_lab_beta_);
    boson_lab.Boost(cm_to_lab_beta_);

    event.electron_in_lab = electron_in_lab_;
    event.ion_in_lab = ion_in_lab_;
    event.electron_out_lab = electron_out_lab;
    event.ion_out_lab = ion_out_lab;
    event.boson_lab = boson_lab;
    event.t = t;
    event.m_e_boson = pair_mass;
    event.s_tilde = s_tilde;
    event.u_tilde = u_tilde;
    event.t2 = t2;
    event.amplitude_reduced = reduced_amplitude;
    event.density_pb = density_pb;
    if (!event.finite()) return false;
    if (cfg_.integrate_paper_cut &&
        !darkboson::passes_paper_cut(event, selection_mass(cfg_))) {
      return false;
    }
    return true;
  }

  double sqrt_s() const { return sqrt_s_; }
  double t_min() const { return t_min_; }
  double t_max() const { return t_max_; }

 private:
  void calculate_global_t_bounds() {
    const HighPrecision hs(s_);
    const HighPrecision hsqrt = sqrt(hs);
    const HighPrecision hion(cfg_.ion_mass);
    const HighPrecision helectron(kElectronMass);
    const HighPrecision hpair(kElectronMass + cfg_.mass);
    const HighPrecision initial_e = hp_ecm(hsqrt, hion, helectron);
    const HighPrecision final_e = hp_ecm(hsqrt, hion, hpair);
    const HighPrecision initial_p = hp_pcm(hsqrt, hion, helectron);
    const HighPrecision final_p = hp_pcm(hsqrt, hion, hpair);
    const HighPrecision ion_mass2 = hion * hion;
    const HighPrecision h_t_min =
        2 * (initial_e * final_e - initial_p * final_p - ion_mass2);
    const HighPrecision h_t_max =
        2 * (initial_e * final_e + initial_p * final_p - ion_mass2);
    t_min_ = h_t_min.convert_to<double>();
    t_max_ = h_t_max.convert_to<double>();
  }

  double pair_mass_max(double t) const {
    const double initial_ion_e =
        ecm(sqrt_s_, cfg_.ion_mass, kElectronMass);
    const double numerator =
        initial_ion_e * (2.0 * cfg_.ion_mass * cfg_.ion_mass + t) -
        p_initial_cm_ * std::sqrt(t * (4.0 * cfg_.ion_mass * cfg_.ion_mass + t));
    const double max_mass2 =
        s_ + cfg_.ion_mass * cfg_.ion_mass -
        numerator / (cfg_.ion_mass * cfg_.ion_mass / sqrt_s_);
    return max_mass2 > 0.0 ? std::sqrt(max_mass2) : 0.0;
  }

  GeneratorConfig cfg_;
  TLorentzVector electron_in_lab_;
  TLorentzVector ion_in_lab_;
  TLorentzVector total_lab_;
  TLorentzVector electron_initial_cm_;
  TLorentzVector ion_initial_cm_;
  TVector3 cm_to_lab_beta_;
  double sqrt_s_ = 0.0;
  double s_ = 0.0;
  double p_initial_cm_ = 0.0;
  double t_min_ = 0.0;
  double t_max_ = 0.0;
};

double parse_double(const std::string& value, const std::string& option) {
  try {
    return std::stod(value);
  } catch (...) {
    throw std::runtime_error("Invalid numeric value for " + option + ": " +
                             value);
  }
}

long long parse_integer(const std::string& value, const std::string& option) {
  try {
    return std::stoll(value);
  } catch (...) {
    throw std::runtime_error("Invalid integer value for " + option + ": " +
                             value);
  }
}

void print_help(const char* program) {
  std::cout
      << "Usage: " << program << " [options]\n\n"
      << "  --mass GeV                 Vector-boson mass (default 1)\n"
      << "  --coupling value           Electron coupling (default 1e-4)\n"
      << "  --cut-mass GeV             Mass hypothesis used for Table I cuts\n"
      << "  --events N                 Generated weighted events\n"
      << "  --cells N                  TFoam adaptive cells\n"
      << "  --samples N                TFoam samples per cell\n"
      << "  --seed N                   Random seed\n"
      << "  --output path.root         Output ROOT file\n"
      << "  --electron-energy GeV      Electron beam energy\n"
      << "  --ion-energy-per-A GeV     Ion energy per nucleon\n"
      << "  --ion-mass GeV             Gold-ion mass\n"
      << "  --integrate-paper-cut      Adapt directly to the selected phase space\n"
      << "  --quiet                     Suppress TFoam progress\n"
      << "  --help                      Show this message\n";
}

GeneratorConfig parse_arguments(int argc, char** argv) {
  GeneratorConfig cfg;
  for (int i = 1; i < argc; ++i) {
    const std::string option = argv[i];
    auto value = [&]() -> std::string {
      if (i + 1 >= argc) {
        throw std::runtime_error("Missing value after " + option);
      }
      return argv[++i];
    };
    if (option == "--mass") {
      cfg.mass = parse_double(value(), option);
    } else if (option == "--coupling") {
      cfg.coupling = parse_double(value(), option);
    } else if (option == "--cut-mass") {
      cfg.cut_mass = parse_double(value(), option);
    } else if (option == "--events") {
      cfg.events = parse_integer(value(), option);
    } else if (option == "--cells") {
      cfg.cells = static_cast<int>(parse_integer(value(), option));
    } else if (option == "--samples") {
      cfg.samples = static_cast<int>(parse_integer(value(), option));
    } else if (option == "--seed") {
      cfg.seed = static_cast<unsigned long>(parse_integer(value(), option));
    } else if (option == "--output") {
      cfg.output = value();
    } else if (option == "--electron-energy") {
      cfg.electron_energy = parse_double(value(), option);
    } else if (option == "--ion-energy-per-A") {
      cfg.ion_energy_per_nucleon = parse_double(value(), option);
    } else if (option == "--ion-mass") {
      cfg.ion_mass = parse_double(value(), option);
    } else if (option == "--integrate-paper-cut") {
      cfg.integrate_paper_cut = true;
    } else if (option == "--quiet") {
      cfg.quiet = true;
    } else if (option == "--help" || option == "-h") {
      print_help(argv[0]);
      std::exit(0);
    } else {
      throw std::runtime_error("Unknown option: " + option);
    }
  }
  if (!(cfg.mass > 0.0 && cfg.coupling > 0.0 && cfg.events > 0 &&
        cfg.cells > 0 && cfg.samples > 0)) {
    throw std::runtime_error("Mass, coupling, events, cells, and samples must be positive");
  }
  return cfg;
}

std::string configuration_string(const GeneratorConfig& cfg,
                                 const VectorBosonDensity& density) {
  std::ostringstream out;
  out << std::setprecision(12)
      << "process=vector;mass_GeV=" << cfg.mass
      << ";cut_mass_GeV=" << selection_mass(cfg)
      << ";coupling=" << cfg.coupling
      << ";electron_energy_GeV=" << cfg.electron_energy
      << ";ion_energy_per_nucleon_GeV=" << cfg.ion_energy_per_nucleon
      << ";ion_mass_GeV=" << cfg.ion_mass
      << ";A=" << cfg.mass_number << ";Z=" << cfg.charge_number
      << ";sqrt_s_GeV=" << density.sqrt_s()
      << ";t_min_GeV2=" << density.t_min()
      << ";t_max_GeV2=" << density.t_max()
      << ";events=" << cfg.events << ";cells=" << cfg.cells
      << ";samples=" << cfg.samples << ";seed=" << cfg.seed;
  out << ";integrate_paper_cut=" << (cfg.integrate_paper_cut ? 1 : 0);
  return out.str();
}

}  // namespace

namespace darkboson {

bool EventKinematics::finite() const {
  const auto vector_finite = [](const TLorentzVector& p) {
    return std::isfinite(p.Px()) && std::isfinite(p.Py()) &&
           std::isfinite(p.Pz()) && std::isfinite(p.E());
  };
  return vector_finite(electron_in_lab) && vector_finite(ion_in_lab) &&
         vector_finite(electron_out_lab) && vector_finite(ion_out_lab) &&
         vector_finite(boson_lab) && std::isfinite(t) &&
         std::isfinite(m_e_boson) && std::isfinite(s_tilde) &&
         std::isfinite(u_tilde) && std::isfinite(t2) &&
         std::isfinite(amplitude_reduced) && std::isfinite(density_pb);
}

PaperCut paper_cut_for_mass(double mass) {
  static const std::array<PaperCut, 11> cuts = {{
      {0.010, std::pow(10.0, -0.7), 1.1, -3.5, -1.5, 10.0},
      {0.032, std::pow(10.0, -0.7), 1.1, -3.5, -1.5, 10.0},
      {0.100, std::pow(10.0, -0.7), 1.1, -3.5, -1.5, 10.0},
      {0.316, std::pow(10.0, -0.7), 1.1, -3.5, -1.5, 10.0},
      {1.000, std::pow(10.0, 0.2), 1.3, -3.5, 2.0, 10.0},
      {1.585, std::pow(10.0, 0.5), 1.3, -3.0, 2.0, 10.0},
      {2.512, std::pow(10.0, 0.8), 1.3, -2.5, 2.5, 10.0},
      {3.981, std::pow(10.0, 1.2), 1.3, -2.5, 1.0, 10.0},
      {5.000, std::pow(10.0, 1.4), 1.3, -3.0, 1.0, 10.0},
      {6.310, std::pow(10.0, 1.5), 1.3, -2.0, 3.5, 10.0},
      {10.000, std::pow(10.0, 1.5), 1.3, -1.5, 3.0, 10.0},
  }};
  return *std::min_element(
      cuts.begin(), cuts.end(), [mass](const PaperCut& a, const PaperCut& b) {
        return std::abs(std::log(a.mass / mass)) <
               std::abs(std::log(b.mass / mass));
      });
}

bool passes_paper_cut(const EventKinematics& event, double mass) {
  const PaperCut cut = paper_cut_for_mass(mass);
  const double eta = event.electron_out_lab.Eta();
  return event.electron_q2() > cut.qe2_min &&
         event.electron_out_lab.Pt() > cut.pt_min && eta > cut.eta_min &&
         eta < cut.eta_max && event.electron_out_lab.E() < cut.energy_max;
}

}  // namespace darkboson

int main(int argc, char** argv) {
  try {
    const GeneratorConfig cfg = parse_arguments(argc, argv);
    std::filesystem::path output_path(cfg.output);
    if (output_path.has_parent_path()) {
      std::filesystem::create_directories(output_path.parent_path());
    }

    VectorBosonDensity density(cfg);
    TRandom3 random(cfg.seed);
    TFoam foam("dark_boson_foam");
    foam.SetkDim(4);
    foam.SetnCells(cfg.cells);
    foam.SetnSampl(cfg.samples);
    foam.SetnBin(cfg.bins);
    foam.SetOptRej(0);
    foam.SetOptDrive(2);
    foam.SetEvPerBin(25);
    foam.SetChat(cfg.quiet ? 0 : 1);
    foam.SetRho(&density);
    foam.SetPseRan(&random);

    if (!cfg.quiet) {
      std::cout << "Initializing adaptive phase-space sampler\n"
                << configuration_string(cfg, density) << "\n";
    }
    foam.Initialize();

    TFile output(cfg.output.c_str(), "RECREATE");
    if (output.IsZombie()) {
      throw std::runtime_error("Could not create output file: " + cfg.output);
    }

    TTree events("events", "Weighted coherent e Au -> e Au phi events");
    Long64_t event_number = 0;
    double foam_weight = 0.0;
    double mass = cfg.mass;
    double cut_mass = selection_mass(cfg);
    double coupling = cfg.coupling;
    double e_px = 0.0, e_py = 0.0, e_pz = 0.0, e_energy = 0.0;
    double phi_px = 0.0, phi_py = 0.0, phi_pz = 0.0, phi_energy = 0.0;
    double phi_eta = 0.0, photon_miss_probability = 0.0;
    double ion_px = 0.0, ion_py = 0.0, ion_pz = 0.0, ion_energy = 0.0;
    double electron_pt = 0.0, electron_eta = 0.0;
    double qe2 = 0.0, qa2 = 0.0, pair_mass = 0.0;
    double s_tilde = 0.0, u_tilde = 0.0, t2 = 0.0;
    double reduced_amplitude = 0.0, density_pb = 0.0;
    bool pass_paper_cut = false;

    events.Branch("event", &event_number);
    events.Branch("foam_weight", &foam_weight);
    events.Branch("mass", &mass);
    events.Branch("cut_mass", &cut_mass);
    events.Branch("coupling", &coupling);
    events.Branch("electron_px", &e_px);
    events.Branch("electron_py", &e_py);
    events.Branch("electron_pz", &e_pz);
    events.Branch("electron_energy", &e_energy);
    events.Branch("electron_pt", &electron_pt);
    events.Branch("electron_eta", &electron_eta);
    events.Branch("boson_px", &phi_px);
    events.Branch("boson_py", &phi_py);
    events.Branch("boson_pz", &phi_pz);
    events.Branch("boson_energy", &phi_energy);
    events.Branch("boson_eta", &phi_eta);
    events.Branch("photon_miss_probability", &photon_miss_probability);
    events.Branch("ion_px", &ion_px);
    events.Branch("ion_py", &ion_py);
    events.Branch("ion_pz", &ion_pz);
    events.Branch("ion_energy", &ion_energy);
    events.Branch("Qe2", &qe2);
    events.Branch("QA2", &qa2);
    events.Branch("pair_mass", &pair_mass);
    events.Branch("s_tilde", &s_tilde);
    events.Branch("u_tilde", &u_tilde);
    events.Branch("t2", &t2);
    events.Branch("reduced_amplitude", &reduced_amplitude);
    events.Branch("density_pb", &density_pb);
    events.Branch("pass_paper_cut", &pass_paper_cut);

    TH1D h_pt("electron_pt", ";p_{T}^{e} [GeV];d#sigma/dp_{T}^{e} [pb/GeV]",
              100, 0.0, 20.0);
    TH1D h_eta("electron_eta", ";#eta_{e};d#sigma/d#eta_{e} [pb]", 100,
               -7.0, 5.0);
    TH1D h_energy("electron_energy", ";E_{e} [GeV];d#sigma/dE_{e} [pb/GeV]",
                  100, 0.0, 18.1);
    TH1D h_log_qe2("log10_Qe2", ";log_{10}(Q_{e}^{2}/GeV^{2});d#sigma/dlog_{10}Q_{e}^{2} [pb]",
                   120, -8.0, 4.0);
    TH1D h_log_qa2("log10_QA2", ";log_{10}(Q_{A}^{2}/GeV^{2});d#sigma/dlog_{10}Q_{A}^{2} [pb]",
                   120, -16.0, 2.0);
    TH2D h_qe2_qa2("Qe2_vs_QA2",
                   ";log_{10}(Q_{A}^{2}/GeV^{2});log_{10}(Q_{e}^{2}/GeV^{2})",
                   100, -16.0, 2.0, 100, -8.0, 4.0);
    for (TH1* histogram : {static_cast<TH1*>(&h_pt), static_cast<TH1*>(&h_eta),
                           static_cast<TH1*>(&h_energy),
                           static_cast<TH1*>(&h_log_qe2),
                           static_cast<TH1*>(&h_log_qa2),
                           static_cast<TH1*>(&h_qe2_qa2)}) {
      histogram->Sumw2();
    }

    double sum_weights = 0.0;
    double sum_cut_weights = 0.0;
    double sum_qe2_weights = 0.0;
    double sum_qe2_pt_weights = 0.0;
    double sum_qe2_pt_eta_weights = 0.0;
    double sum_cut_flipped_eta_weights = 0.0;
    long long accepted_events = 0;
    std::array<double, 4> point{};

    for (event_number = 0; event_number < cfg.events; ++event_number) {
      foam.MakeEvent();
      foam.GetMCvect(point.data());
      foam_weight = foam.GetMCwt();

      darkboson::EventKinematics event;
      if (!density.build_event(point.data(), event, density_pb)) continue;

      e_px = event.electron_out_lab.Px();
      e_py = event.electron_out_lab.Py();
      e_pz = event.electron_out_lab.Pz();
      e_energy = event.electron_out_lab.E();
      electron_pt = event.electron_out_lab.Pt();
      electron_eta = event.electron_out_lab.Eta();
      phi_px = event.boson_lab.Px();
      phi_py = event.boson_lab.Py();
      phi_pz = event.boson_lab.Pz();
      phi_energy = event.boson_lab.E();
      phi_eta = event.boson_lab.Eta();
      photon_miss_probability = std::abs(phi_eta) > 3.5 ? 1.0 : 1.0e-6;
      ion_px = event.ion_out_lab.Px();
      ion_py = event.ion_out_lab.Py();
      ion_pz = event.ion_out_lab.Pz();
      ion_energy = event.ion_out_lab.E();
      qe2 = event.electron_q2();
      qa2 = event.t;
      pair_mass = event.m_e_boson;
      s_tilde = event.s_tilde;
      u_tilde = event.u_tilde;
      t2 = event.t2;
      reduced_amplitude = event.amplitude_reduced;
      pass_paper_cut =
          darkboson::passes_paper_cut(event, selection_mass(cfg));

      ++accepted_events;
      sum_weights += foam_weight;
      if (pass_paper_cut) sum_cut_weights += foam_weight;
      const darkboson::PaperCut cut =
          darkboson::paper_cut_for_mass(selection_mass(cfg));
      const bool pass_qe2 = qe2 > cut.qe2_min;
      const bool pass_pt = electron_pt > cut.pt_min;
      const bool pass_eta = electron_eta > cut.eta_min && electron_eta < cut.eta_max;
      const bool pass_energy = e_energy < cut.energy_max;
      const bool pass_flipped_eta = -electron_eta > cut.eta_min &&
                                    -electron_eta < cut.eta_max;
      if (pass_qe2) sum_qe2_weights += foam_weight;
      if (pass_qe2 && pass_pt) sum_qe2_pt_weights += foam_weight;
      if (pass_qe2 && pass_pt && pass_eta) {
        sum_qe2_pt_eta_weights += foam_weight;
      }
      if (pass_qe2 && pass_pt && pass_flipped_eta && pass_energy) {
        sum_cut_flipped_eta_weights += foam_weight;
      }
      h_pt.Fill(electron_pt, foam_weight);
      h_eta.Fill(electron_eta, foam_weight);
      h_energy.Fill(e_energy, foam_weight);
      if (qe2 > 0.0) h_log_qe2.Fill(std::log10(qe2), foam_weight);
      if (qa2 > 0.0) h_log_qa2.Fill(std::log10(qa2), foam_weight);
      if (qe2 > 0.0 && qa2 > 0.0) {
        h_qe2_qa2.Fill(std::log10(qa2), std::log10(qe2), foam_weight);
      }
      events.Fill();
    }

    double sigma_total_pb = 0.0;
    double sigma_total_error_pb = 0.0;
    foam.GetIntegMC(sigma_total_pb, sigma_total_error_pb);
    const double event_normalization =
        sum_weights > 0.0 ? sigma_total_pb / sum_weights : 0.0;
    const double sigma_cut_pb =
        sum_weights > 0.0 ? sigma_total_pb * sum_cut_weights / sum_weights
                          : 0.0;
    const auto normalized_cross_section = [&](double selected_weight) {
      return sum_weights > 0.0 ? sigma_total_pb * selected_weight / sum_weights
                               : 0.0;
    };

    for (TH1* histogram : {static_cast<TH1*>(&h_pt), static_cast<TH1*>(&h_eta),
                           static_cast<TH1*>(&h_energy),
                           static_cast<TH1*>(&h_log_qe2),
                           static_cast<TH1*>(&h_log_qa2),
                           static_cast<TH1*>(&h_qe2_qa2)}) {
      histogram->Scale(event_normalization, "width");
    }

    const std::string config_text = configuration_string(cfg, density);
    TNamed config_metadata("generator_configuration", config_text.c_str());
    TParameter<double> p_sigma_total("sigma_total_pb", sigma_total_pb);
    TParameter<double> p_sigma_error("sigma_total_error_pb",
                                     sigma_total_error_pb);
    TParameter<double> p_sigma_cut("sigma_paper_cut_pb", sigma_cut_pb);
    TParameter<double> p_event_norm("pb_per_foam_weight",
                                    event_normalization);
    TParameter<double> p_sum_weights("sum_foam_weights", sum_weights);
    TParameter<Long64_t> p_accepted("accepted_events", accepted_events);

    output.cd();
    events.Write();
    h_pt.Write();
    h_eta.Write();
    h_energy.Write();
    h_log_qe2.Write();
    h_log_qa2.Write();
    h_qe2_qa2.Write();
    config_metadata.Write();
    p_sigma_total.Write();
    p_sigma_error.Write();
    p_sigma_cut.Write();
    p_event_norm.Write();
    p_sum_weights.Write();
    p_accepted.Write();
    output.Close();

    std::cout << std::setprecision(8)
              << "mass_GeV=" << cfg.mass << "\n"
              << "sqrt_s_GeV=" << density.sqrt_s() << "\n"
              << "t_range_GeV2=[" << density.t_min() << ", "
              << density.t_max() << "]\n"
              << "accepted_events=" << accepted_events << "\n"
              << "sigma_total_pb=" << sigma_total_pb << " +/- "
              << sigma_total_error_pb << "\n"
              << "sigma_after_Qe2_pb="
              << normalized_cross_section(sum_qe2_weights) << "\n"
              << "sigma_after_Qe2_pt_pb="
              << normalized_cross_section(sum_qe2_pt_weights) << "\n"
              << "sigma_after_Qe2_pt_eta_pb="
              << normalized_cross_section(sum_qe2_pt_eta_weights) << "\n"
              << "sigma_paper_cut_pb=" << sigma_cut_pb << "\n"
              << "sigma_cut_flipped_eta_pb="
              << normalized_cross_section(sum_cut_flipped_eta_weights) << "\n"
              << "output=" << cfg.output << "\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Error: " << error.what() << "\n";
    return 1;
  }
}
