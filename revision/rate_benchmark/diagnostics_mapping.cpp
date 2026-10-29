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

namespace Orig {

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
  std::string photon_region = "all";
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
    const double abs_photon_eta = std::abs(event.boson_lab.Eta());
    if (cfg_.photon_region == "effective") {
      density_pb *= abs_photon_eta > 3.5 ? 1.0 : 1.0e-6;
      event.density_pb = density_pb;
    }
    if (cfg_.photon_region == "central" && abs_photon_eta > 3.5) {
      return false;
    }
    if (cfg_.photon_region == "forward" && abs_photon_eta <= 3.5) {
      return false;
    }
    return true;
  }

  double sqrt_s() const { return sqrt_s_; }
  double t_min() const { return t_min_; }
  double t_max() const { return t_max_; }

 public:
  double validation_pair_max(double t) const {return pair_mass_max(t);}
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
      << "  --photon-region name       all, central, forward, or effective\n"
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
    } else if (option == "--photon-region") {
      cfg.photon_region = value();
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
  if (cfg.photon_region != "all" && cfg.photon_region != "central" &&
      cfg.photon_region != "forward" && cfg.photon_region != "effective") {
    throw std::runtime_error(
        "Photon region must be all, central, forward, or effective");
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
  out << ";photon_region=" << cfg.photon_region;
  out << ";integrate_paper_cut=" << (cfg.integrate_paper_cut ? 1 : 0);
  return out.str();
}

}  // namespace
namespace Lab {

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
  std::string photon_region = "all";
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
    // Four lab coordinates: electron eta and energy, photon polar cosine,
    // and relative azimuth. The global electron azimuth is integrated analytically.
    const auto cut = darkboson::paper_cut_for_mass(selection_mass(cfg_));
    const double eta_hi = std::min(cut.eta_max, std::acosh(std::sqrt(cut.energy_max*cut.energy_max-kElectronMass*kElectronMass)/cut.pt_min));
    const double eta_e = cut.eta_min + x[0]*(eta_hi-cut.eta_min);
    const double ch = std::cosh(eta_e);
    const double min_energy = std::sqrt(kElectronMass*kElectronMass+std::pow(cut.pt_min*ch,2));
    if (!(cut.energy_max>min_energy)) return false;
    const double energy_e = min_energy+x[1]*(cut.energy_max-min_energy);
    const double momentum_e = std::sqrt(energy_e*energy_e-kElectronMass*kElectronMass);
    TLorentzVector electron_out_lab(momentum_e/ch,0,momentum_e*std::tanh(eta_e),energy_e);
    const double edge=std::tanh(3.5);
    double cg=0,jac_cos=0;
    if(cfg_.photon_region=="central") { cg=-edge+2*edge*x[2];jac_cos=2*edge; }
    else if(cfg_.photon_region=="outside") {
      if(x[2]<0.5) cg=-1+2*(1-edge)*x[2];
      else cg=edge+2*(1-edge)*(x[2]-0.5);
      jac_cos=2*(1-edge);
    } else {cg=-1+2*x[2];jac_cos=2;}
    const double sg=std::sqrt(std::max(0.,1-cg*cg));
    const double phi=2*TMath::Pi()*x[3];
    const TVector3 direction(sg*std::cos(phi),sg*std::sin(phi),cg);
    const TLorentzVector available=electron_in_lab_+ion_in_lab_-electron_out_lab;
    const double apar=available.Vect().Dot(direction), a0=available.E();
    const double d=(available.M2()+cfg_.mass*cfg_.mass-cfg_.ion_mass*cfg_.ion_mass)/2;
    const double denominator=a0*a0-apar*apar;
    const double radicand=d*d-cfg_.mass*cfg_.mass*denominator;
    if (!(d>0 && denominator>0 && radicand>=0)) return false;
    const double energy_g=(a0*d+apar*std::sqrt(radicand))/denominator;
    if (!(energy_g>cfg_.mass)) return false;
    const double momentum_g=std::sqrt(energy_g*energy_g-cfg_.mass*cfg_.mass);
    TLorentzVector boson_lab(momentum_g*direction,energy_g);
    const TLorentzVector ion_out_lab=available-boson_lab;
    if (!(ion_out_lab.E()>0)) return false;
    const double t=-(electron_in_lab_-electron_out_lab-boson_lab).M2();
    if (!(t>0 && std::isfinite(t))) return false;
    event.electron_in_lab=electron_in_lab_;event.ion_in_lab=ion_in_lab_;
    event.electron_out_lab=electron_out_lab;event.ion_out_lab=ion_out_lab;event.boson_lab=boson_lab;
    event.t=t;event.m_e_boson=(electron_out_lab+boson_lab).M();
    if (!darkboson::passes_paper_cut(event,selection_mass(cfg_))) return false;
    const TLorentzVector nuclear_sum=ion_in_lab_+ion_out_lab;
    const double s_tilde=(electron_out_lab+boson_lab).M2()-kElectronMass*kElectronMass;
    const double u_tilde=(electron_in_lab_-boson_lab).M2()-kElectronMass*kElectronMass;
    const double t2=(electron_out_lab-electron_in_lab_).M2();
    const double st_plus_ut = s_tilde + u_tilde;
    const double st_ut = s_tilde * u_tilde;
    if (std::abs(st_ut) < 1.0e-30 || std::abs(st_plus_ut) < 1.0e-30) {
      return false;
    }

    const double p_dot_in = nuclear_sum.Dot(electron_in_lab_);
    const double p_dot_out = nuclear_sum.Dot(electron_out_lab);
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


    const double form_factor=helm_form_factor(t,cfg_.mass_number);
    const double matrix_squared=std::pow(kElectricCharge,4)*cfg_.coupling*cfg_.coupling*cfg_.charge_number*cfg_.charge_number*std::pow(form_factor/t,2)*reduced_amplitude;
    // dPhi3/(4 p_initial sqrt(s)), after integrating the global azimuth.
    const double shell_jac=std::abs(a0*momentum_g-energy_g*apar);
    if (!(shell_jac>0)) return false;
    const double phase=momentum_e*momentum_g*momentum_g/(std::pow(2*TMath::Pi(),4)*32*p_initial_cm_*sqrt_s_*shell_jac);
    const double map_jac=(eta_hi-cut.eta_min)*(cut.energy_max-min_energy)/(ch*ch)*jac_cos*(2*TMath::Pi());
    density_pb=matrix_squared*phase*map_jac*kGeV2ToPb;
    if (!(density_pb>=0 && std::isfinite(density_pb))) return false;
    event.s_tilde=s_tilde;event.u_tilde=u_tilde;event.t2=t2;
    event.amplitude_reduced=reduced_amplitude;event.density_pb=density_pb;
    return event.finite();
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
    } else if (option == "--photon-region") {
      cfg.photon_region = value();
      if (cfg.photon_region != "all" && cfg.photon_region != "central" && cfg.photon_region != "outside") throw std::runtime_error("invalid photon region");
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
  out << ";phase_space_mapping=lab;photon_region=" << cfg.photon_region;
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

#include <fstream>
#include <random>
#include <set>
std::array<double,4> inverse(const darkboson::EventKinematics& e,const Orig::VectorBosonDensity& o){
 auto pin=e.electron_in_lab+e.ion_in_lab;auto beta=pin.BoostVector();
 auto ion=e.ion_out_lab,bos=e.boson_lab,ele=e.electron_out_lab;
 ion.Boost(-beta);bos.Boost(-beta);ele.Boost(-beta);
 double angle=std::atan2(ion.Py(),ion.Px());ion.RotateZ(-angle);bos.RotateZ(-angle);ele.RotateZ(-angle);
 auto pair=ele+bos;double M=pair.M();bos.Boost(-pair.BoostVector());
 double minpair=.00051099895+1e-6,maxpair=o.validation_pair_max(e.t);
 std::array<double,4> x={std::log(e.t/o.t_min())/std::log(o.t_max()/o.t_min()),(M-minpair)/(maxpair-minpair),(bos.Pz()/bos.P()+1)/2,0};
 double phi=std::atan2(bos.Py(),bos.Px());if(phi<0)phi+=2*TMath::Pi();x[3]=phi/(2*TMath::Pi());return x;
}
double determinant(double a[4][4]){
 double d=1;for(int i=0;i<4;i++){
  int p=i;for(int j=i+1;j<4;j++)if(std::abs(a[j][i])>std::abs(a[p][i]))p=j;
  if(p!=i){for(int k=0;k<4;k++)std::swap(a[i][k],a[p][k]);d=-d;}
  double v=a[i][i];d*=v;if(v==0)return 0;
  for(int j=i+1;j<4;j++){double f=a[j][i]/v;for(int k=i+1;k<4;k++)a[j][k]-=f*a[i][k];}
 }return d;
}
int main(int argc,char** argv){
 if(argc!=4){std::cerr<<"Usage: diagnostics_mapping outside.root cutmass output-prefix\n";return 2;}
 double cutmass=std::stod(argv[2]);std::string prefix=argv[3];
 Orig::GeneratorConfig c;c.mass=1e-6;c.cut_mass=cutmass;c.coupling=.3028221209;c.integrate_paper_cut=true;c.photon_region="all";
 Orig::VectorBosonDensity o(c);
 Lab::GeneratorConfig l;l.mass=c.mass;l.cut_mass=cutmass;l.coupling=c.coupling;l.integrate_paper_cut=true;l.photon_region="outside";
 Lab::VectorBosonDensity d(l);
 TFile file(argv[1],"READ");auto*tree=dynamic_cast<TTree*>(file.Get("events"));if(file.IsZombie()||!tree)return 3;
 double eta,energy,bpx,bpy,bpz,w,old_t;
 tree->SetBranchStatus("*",0);
 for(const char*n:{"electron_eta","electron_energy","boson_px","boson_py","boson_pz","foam_weight","QA2"})tree->SetBranchStatus(n,1);
 tree->SetBranchAddress("electron_eta",&eta);tree->SetBranchAddress("electron_energy",&energy);
 tree->SetBranchAddress("boson_px",&bpx);tree->SetBranchAddress("boson_py",&bpy);tree->SetBranchAddress("boson_pz",&bpz);
 tree->SetBranchAddress("foam_weight",&w);tree->SetBranchAddress("QA2",&old_t);
 auto cut=darkboson::paper_cut_for_mass(cutmass);
 const double edge=std::tanh(3.5),eta_hi=std::min(cut.eta_max,std::acosh(std::sqrt(cut.energy_max*cut.energy_max-std::pow(.00051099895,2))/cut.pt_min));
 std::vector<std::array<double,4>> coords;std::vector<double> weights;std::vector<double> source_t;
 for(Long64_t i=0;i<tree->GetEntries();i++){
  tree->GetEntry(i);double cg=bpz/std::sqrt(bpx*bpx+bpy*bpy+bpz*bpz),ph=std::atan2(bpy,bpx);if(ph<0)ph+=2*TMath::Pi();
  double emin=std::sqrt(std::pow(.00051099895,2)+std::pow(cut.pt_min*std::cosh(eta),2));
  std::array<double,4> u={(eta-cut.eta_min)/(eta_hi-cut.eta_min),(energy-emin)/(cut.energy_max-emin),cg<0?(cg+1)/(2*(1-edge)):.5+(cg-edge)/(2*(1-edge)),ph/(2*TMath::Pi())};
  if(w>0&&std::isfinite(w)){coords.push_back(u);weights.push_back(w);source_t.push_back(old_t);}
 }
 std::mt19937 rng(654210);std::discrete_distribution<size_t> draw(weights.begin(),weights.end());std::set<size_t> unique;
 std::ofstream points(prefix+".csv");points<<std::setprecision(17)<<"entry,cut_mass_GeV,electron_energy_GeV,electron_eta,t_GeV2,source_t_relative_error,cm_t_relative_error,cm_energy_relative_error,rho_lab_pb,rho_cm_pb,ratio_h1e5,ratio_h3e6,ratio_h1e6,step_ratio_spread,lab_u0,lab_u1,lab_u2,lab_u3,cm_x0,cm_x1,cm_x2,cm_x3,pair_mass_GeV\n";
 int accepted=0,attempts=0,labfail=0,cmfail=0,jacfail=0;double maxerr=0,maxspread=0,maxt=0,maxcmE=0,maxcmt=0,tmin=1e99,tmax=0;
 std::vector<double> relerrors;
 while(attempts<500&&accepted<100){
  ++attempts;size_t index=draw(rng);auto u=coords[index];darkboson::EventKinematics e;double rho;
  if(!d.build_event(u.data(),e,rho)||rho<1e-80){++labfail;continue;}
  auto x=inverse(e,o);darkboson::EventKinematics e2;double rho2;
  if(!o.build_event(x.data(),e2,rho2)||rho2<1e-90){++cmfail;continue;}
  std::array<double,3> ratios{};bool ok=true;
  for(int step=0;step<3;step++){
   double base=step==0?1e-5:(step==1?3e-6:1e-6),jac[4][4];
   for(int j=0;j<4;j++){
    auto up=u,um=u;double h=std::min(base,.05*std::min(u[j],1-u[j]));if(h<=1e-11){ok=false;break;}
    up[j]+=h;um[j]-=h;darkboson::EventKinematics ep,em;double z;
    if(!d.build_event(up.data(),ep,z)||!d.build_event(um.data(),em,z)){ok=false;break;}
    auto xp=inverse(ep,o),xm=inverse(em,o);
    for(int k=0;k<4;k++){double v=xp[k]-xm[k];if(k==3){if(v>.5)v-=1;if(v<-.5)v+=1;}jac[k][j]=v/(2*h);}
   }
   if(!ok)break;
   ratios[step]=rho/(rho2*std::abs(determinant(jac)));if(!std::isfinite(ratios[step])){ok=false;break;}
  }
  if(!ok){++jacfail;continue;}
  double spread=*std::max_element(ratios.begin(),ratios.end())-*std::min_element(ratios.begin(),ratios.end());
  double err=std::abs(ratios[2]-1),terr=std::abs(e.t/source_t[index]-1),cmt=std::abs(e2.t/e.t-1),cmE=std::abs(e2.electron_out_lab.E()/e.electron_out_lab.E()-1);
  maxerr=std::max(maxerr,err);maxspread=std::max(maxspread,spread);maxt=std::max(maxt,terr);maxcmE=std::max(maxcmE,cmE);maxcmt=std::max(maxcmt,cmt);
  tmin=std::min(tmin,e.t);tmax=std::max(tmax,e.t);++accepted;unique.insert(index);relerrors.push_back(err);
  points<<index<<","<<cutmass<<","<<e.electron_out_lab.E()<<","<<e.electron_out_lab.Eta()<<","<<e.t<<","<<terr<<","<<cmt<<","<<cmE<<","<<rho<<","<<rho2;
  for(double ratio:ratios)points<<","<<ratio;points<<","<<spread;for(double v:u)points<<","<<v;for(double v:x)points<<","<<v;points<<","<<e.m_e_boson<<"\n";
 }
 std::sort(relerrors.begin(),relerrors.end());
 std::ostringstream summary;summary<<std::setprecision(17)<<"{\"cut_mass_GeV\":"<<cutmass<<",\"source\":\""<<argv[1]<<"\",\"source_positive_weight_entries\":"<<coords.size()<<",\"weighted_draws\":"<<attempts<<",\"checked_points\":"<<accepted<<",\"unique_checked_points\":"<<unique.size()<<",\"lab_build_failures\":"<<labfail<<",\"cm_build_failures\":"<<cmfail<<",\"jacobian_failures\":"<<jacfail<<",\"maximum_relative_density_error\":"<<maxerr<<",\"median_relative_density_error\":"<<(relerrors.empty()?0:relerrors[relerrors.size()/2])<<",\"maximum_step_ratio_spread\":"<<maxspread<<",\"maximum_source_t_reconstruction_error\":"<<maxt<<",\"maximum_cm_t_roundtrip_error\":"<<maxcmt<<",\"maximum_cm_electron_energy_roundtrip_error\":"<<maxcmE<<",\"t_min_GeV2\":"<<tmin<<",\"t_max_GeV2\":"<<tmax<<"}";
 std::ofstream out(prefix+".json");out<<summary.str()<<"\n";std::cout<<summary.str()<<"\n";
 return accepted>=90&&maxerr<.005?0:1;
}
