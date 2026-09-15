#include <TFoam.h>
#include <TFoamIntegrand.h>
#include <TFile.h>
#include <TMath.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TRandom3.h>
#include <TTree.h>
#include <TLorentzVector.h>
#include <TVector3.h>

#include <boost/multiprecision/cpp_dec_float.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

constexpr double kElectronMass = 0.00051099895000;
constexpr double kAlpha = 1.0 / 137.035999084;
constexpr double kGeV2ToPb = 3.893793721e8;
constexpr double kFmToGeVInv = 5.067730716;
using HighPrecision = boost::multiprecision::cpp_dec_float_50;

double lambda(double x, double y, double z) {
  return x * x + y * y + z * z - 2.0 * x * y - 2.0 * x * z -
         2.0 * y * z;
}

double pcm(double parent, double first, double second) {
  const double value =
      lambda(parent * parent, first * first, second * second);
  return value > 0.0 ? std::sqrt(value) / (2.0 * parent) : 0.0;
}

double ecm(double parent, double first, double second) {
  return (parent * parent + first * first - second * second) /
         (2.0 * parent);
}

HighPrecision hp_lambda(const HighPrecision& x, const HighPrecision& y,
                        const HighPrecision& z) {
  return x * x + y * y + z * z - 2 * x * y - 2 * x * z - 2 * y * z;
}

HighPrecision hp_pcm(const HighPrecision& parent, const HighPrecision& first,
                     const HighPrecision& second) {
  return sqrt(hp_lambda(parent * parent, first * first, second * second)) /
         (2 * parent);
}

HighPrecision hp_ecm(const HighPrecision& parent, const HighPrecision& first,
                     const HighPrecision& second) {
  return (parent * parent + first * first - second * second) / (2 * parent);
}

double helm(double t, int mass_number) {
  const double q = std::sqrt(t);
  const double radius =
      1.1 * std::cbrt(static_cast<double>(mass_number)) * kFmToGeVInv;
  const double skin = 0.9 * kFmToGeVInv;
  const double x = q * radius;
  double factor = 1.0;
  if (std::abs(x) > 1.0e-4) {
    factor = 3.0 * (std::sin(x) / (x * x) - std::cos(x) / x) / x;
  } else {
    const double x2 = x * x;
    factor = 1.0 - x2 / 10.0 + x2 * x2 / 280.0;
  }
  return factor * std::exp(-0.5 * q * q * skin * skin);
}

struct Cut {
  double mass;
  double qe2_min;
  double pt_min;
  double eta_min;
  double eta_max;
  double energy_max;
};

Cut cut_for_mass(double mass) {
  static const std::array<Cut, 11> cuts{{
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
      cuts.begin(), cuts.end(), [mass](const Cut& first, const Cut& second) {
        return std::abs(std::log(first.mass / mass)) <
               std::abs(std::log(second.mass / mass));
      });
}

struct Config {
  double mass = 1.0;
  double coupling = 1.0e-4;
  double electron_energy = 18.0;
  double ion_energy_per_nucleon = 100.0;
  double ion_mass = 183.0;
  int mass_number = 197;
  int charge_number = 79;
  long long events = 100000;
  int cells = 8000;
  int samples = 1000;
  unsigned long seed = 260811101;
  bool selected = false;
  std::string output;
};

struct ScalarEvent {
  double electron_px = 0.0;
  double electron_py = 0.0;
  double electron_pz = 0.0;
  double electron_energy = 0.0;
  double electron_pt = 0.0;
  double electron_eta = 0.0;
  double boson_px = 0.0;
  double boson_py = 0.0;
  double boson_pz = 0.0;
  double boson_energy = 0.0;
  double ion_px = 0.0;
  double ion_py = 0.0;
  double ion_pz = 0.0;
  double ion_energy = 0.0;
  double qe2 = 0.0;
  double qa2 = 0.0;
  double pair_mass = 0.0;
  double s_tilde = 0.0;
  double u_tilde = 0.0;
  double t2 = 0.0;
  double reduced_amplitude = 0.0;
  double density_pb = 0.0;
};

class ScalarDensity final : public TFoamIntegrand {
 public:
  explicit ScalarDensity(const Config& config) : cfg_(config) {
    const double ion_energy = cfg_.mass_number * cfg_.ion_energy_per_nucleon;
    const double electron_p =
        std::sqrt(cfg_.electron_energy * cfg_.electron_energy -
                  kElectronMass * kElectronMass);
    const double ion_p =
        std::sqrt(ion_energy * ion_energy - cfg_.ion_mass * cfg_.ion_mass);
    electron_in_lab_.SetPxPyPzE(0.0, 0.0, -electron_p,
                                cfg_.electron_energy);
    ion_in_lab_.SetPxPyPzE(0.0, 0.0, ion_p, ion_energy);
    const TLorentzVector total = electron_in_lab_ + ion_in_lab_;
    sqrt_s_ = total.M();
    s_ = total.M2();
    cm_to_lab_ = total.BoostVector();
    initial_p_cm_ = pcm(sqrt_s_, cfg_.ion_mass, kElectronMass);
    ion_in_cm_.SetPxPyPzE(0.0, 0.0, initial_p_cm_,
                          ecm(sqrt_s_, cfg_.ion_mass, kElectronMass));
    electron_in_cm_.SetPxPyPzE(0.0, 0.0, -initial_p_cm_,
                               ecm(sqrt_s_, kElectronMass, cfg_.ion_mass));
    calculate_t_bounds();
  }

  Double_t Density(Int_t dimensions, Double_t* random) override {
    return evaluate(dimensions, random, nullptr);
  }

  bool build_event(const double* random, ScalarEvent& event,
                   double& density_pb) {
    density_pb = evaluate(4, const_cast<double*>(random), &event);
    return density_pb > 0.0 && std::isfinite(density_pb);
  }

 private:
  double evaluate(Int_t dimensions, Double_t* random, ScalarEvent* event) {
    if (dimensions != 4) return 0.0;
    const double log_t = std::log(t_max_ / t_min_);
    const double t = t_min_ * std::exp(log_t * random[0]);
    const double jac_t = t * log_t;
    const double min_pair_mass = kElectronMass + cfg_.mass;
    const double max_pair_mass = pair_mass_max(t);
    if (!(max_pair_mass > min_pair_mass)) return 0.0;
    const double pair_mass =
        min_pair_mass + random[1] * (max_pair_mass - min_pair_mass);
    const double jac_pair_mass = max_pair_mass - min_pair_mass;
    const double cos_decay = 2.0 * random[2] - 1.0;
    const double sin_decay =
        std::sqrt(std::max(0.0, 1.0 - cos_decay * cos_decay));
    const double phi = 2.0 * TMath::Pi() * random[3];
    const double jac_angles = 4.0 * TMath::Pi();

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
      return 0.0;
    }
    if (h_one_minus_cos < 0) h_one_minus_cos = 0;
    if (h_one_minus_cos > 2) h_one_minus_cos = 2;
    const double one_minus_cos = h_one_minus_cos.convert_to<double>();
    const double ion_out_p = h_outgoing_p.convert_to<double>();
    const double ion_out_e = h_outgoing_e.convert_to<double>();
    if (!(ion_out_p > 0.0)) return 0.0;
    const double cos_ion = 1.0 - one_minus_cos;
    const double sin_ion =
        std::sqrt(std::max(0.0, one_minus_cos * (2.0 - one_minus_cos)));
    TLorentzVector ion_out_cm(ion_out_p * sin_ion, 0.0,
                              ion_out_p * cos_ion, ion_out_e);
    const TLorentzVector pair_cm =
        electron_in_cm_ + ion_in_cm_ - ion_out_cm;

    const double decay_p = pcm(pair_mass, cfg_.mass, kElectronMass);
    TLorentzVector boson_rest(decay_p * sin_decay * std::cos(phi),
                              decay_p * sin_decay * std::sin(phi),
                              decay_p * cos_decay,
                              ecm(pair_mass, cfg_.mass, kElectronMass));
    TLorentzVector electron_out_rest(
        -boson_rest.Px(), -boson_rest.Py(), -boson_rest.Pz(),
        ecm(pair_mass, kElectronMass, cfg_.mass));
    const TVector3 pair_boost = pair_cm.BoostVector();
    TLorentzVector boson_cm = boson_rest;
    TLorentzVector electron_out_cm = electron_out_rest;
    boson_cm.Boost(pair_boost);
    electron_out_cm.Boost(pair_boost);

    const TLorentzVector nuclear_sum = ion_in_cm_ + ion_out_cm;
    const double s_tilde =
        (electron_out_cm + boson_cm).M2() -
        kElectronMass * kElectronMass;
    const double u_tilde =
        (electron_in_cm_ - boson_cm).M2() -
        kElectronMass * kElectronMass;
    const double sum_su = s_tilde + u_tilde;
    const double product_su = s_tilde * u_tilde;
    if (std::abs(sum_su) < 1.0e-30 || std::abs(product_su) < 1.0e-30) {
      return 0.0;
    }
    const double nuclear_sum2 = nuclear_sum.M2();
    const double p_dot_k = nuclear_sum.Dot(boson_cm);
    const double p_dot_in = nuclear_sum.Dot(electron_in_cm_);
    const double p_dot_out = nuclear_sum.Dot(electron_out_cm);
    const double ratio =
        (u_tilde * p_dot_in + s_tilde * p_dot_out) / sum_su;
    const double coefficient = sum_su * sum_su / product_su;
    const double reduced_amplitude =
        coefficient * nuclear_sum2 -
        4.0 * t / product_su * p_dot_k * p_dot_k +
        sum_su * sum_su /
            (s_tilde * s_tilde * u_tilde * u_tilde) *
            (cfg_.mass * cfg_.mass -
             4.0 * kElectronMass * kElectronMass) *
            (nuclear_sum2 * t - 4.0 * ratio * ratio);
    if (!(reduced_amplitude > 0.0) || !std::isfinite(reduced_amplitude)) {
      return 0.0;
    }

    TLorentzVector electron_out_lab = electron_out_cm;
    electron_out_lab.Boost(cm_to_lab_);

    TLorentzVector ion_out_lab = ion_out_cm;
    TLorentzVector boson_lab = boson_cm;
    ion_out_lab.Boost(cm_to_lab_);
    boson_lab.Boost(cm_to_lab_);
    if (cfg_.selected) {
      const Cut cut = cut_for_mass(cfg_.mass);
      const double qe2 = -(electron_in_lab_ - electron_out_lab).M2();
      const double eta = electron_out_lab.Eta();
      if (!(qe2 > cut.qe2_min && electron_out_lab.Pt() > cut.pt_min &&
            eta > cut.eta_min && eta < cut.eta_max &&
            electron_out_lab.E() < cut.energy_max)) {
        return 0.0;
      }
    }

    const double electric_charge = std::sqrt(4.0 * TMath::Pi() * kAlpha);
    const double form_factor = helm(t, cfg_.mass_number);
    const double coupling_factor =
        std::pow(electric_charge, 4) * cfg_.coupling * cfg_.coupling *
        cfg_.charge_number * cfg_.charge_number;
    const double denominator =
        std::pow(2.0 * TMath::Pi(), 4) * 64.0 * initial_p_cm_ *
        initial_p_cm_ * s_;
    const double density =
        coupling_factor * decay_p / denominator *
        std::pow(form_factor / t, 2) * reduced_amplitude * jac_t *
        jac_pair_mass * jac_angles * kGeV2ToPb;
    if (!(std::isfinite(density) && density >= 0.0)) return 0.0;

    if (event != nullptr) {
      event->electron_px = electron_out_lab.Px();
      event->electron_py = electron_out_lab.Py();
      event->electron_pz = electron_out_lab.Pz();
      event->electron_energy = electron_out_lab.E();
      event->electron_pt = electron_out_lab.Pt();
      event->electron_eta = electron_out_lab.Eta();
      event->boson_px = boson_lab.Px();
      event->boson_py = boson_lab.Py();
      event->boson_pz = boson_lab.Pz();
      event->boson_energy = boson_lab.E();
      event->ion_px = ion_out_lab.Px();
      event->ion_py = ion_out_lab.Py();
      event->ion_pz = ion_out_lab.Pz();
      event->ion_energy = ion_out_lab.E();
      event->qe2 = -(electron_in_lab_ - electron_out_lab).M2();
      event->qa2 = t;
      event->pair_mass = pair_mass;
      event->s_tilde = s_tilde;
      event->u_tilde = u_tilde;
      event->t2 = (electron_out_cm - electron_in_cm_).M2();
      event->reduced_amplitude = reduced_amplitude;
      event->density_pb = density;
    }
    return density;
  }
  void calculate_t_bounds() {
    const HighPrecision hs(s_);
    const HighPrecision root_s = sqrt(hs);
    const HighPrecision ion(cfg_.ion_mass);
    const HighPrecision electron(kElectronMass);
    const HighPrecision pair(kElectronMass + cfg_.mass);
    const HighPrecision initial_e = hp_ecm(root_s, ion, electron);
    const HighPrecision final_e = hp_ecm(root_s, ion, pair);
    const HighPrecision initial_p = hp_pcm(root_s, ion, electron);
    const HighPrecision final_p = hp_pcm(root_s, ion, pair);
    const HighPrecision ion2 = ion * ion;
    t_min_ =
        (2 * (initial_e * final_e - initial_p * final_p - ion2))
            .convert_to<double>();
    t_max_ =
        (2 * (initial_e * final_e + initial_p * final_p - ion2))
            .convert_to<double>();
  }

  double pair_mass_max(double t) const {
    const double initial_ion_e =
        ecm(sqrt_s_, cfg_.ion_mass, kElectronMass);
    const double numerator =
        initial_ion_e * (2.0 * cfg_.ion_mass * cfg_.ion_mass + t) -
        initial_p_cm_ *
            std::sqrt(t * (4.0 * cfg_.ion_mass * cfg_.ion_mass + t));
    const double maximum2 =
        s_ + cfg_.ion_mass * cfg_.ion_mass -
        numerator / (cfg_.ion_mass * cfg_.ion_mass / sqrt_s_);
    return maximum2 > 0.0 ? std::sqrt(maximum2) : 0.0;
  }

  Config cfg_;
  TLorentzVector electron_in_lab_;
  TLorentzVector ion_in_lab_;
  TLorentzVector electron_in_cm_;
  TLorentzVector ion_in_cm_;
  TVector3 cm_to_lab_;
  double sqrt_s_ = 0.0;
  double s_ = 0.0;
  double initial_p_cm_ = 0.0;
  double t_min_ = 0.0;
  double t_max_ = 0.0;
};

}  // namespace

int main(int argc, char** argv) {
  try {
    Config config;
    for (int index = 1; index < argc; ++index) {
      const std::string option = argv[index];
      auto value = [&]() {
        if (++index >= argc) throw std::runtime_error("missing option value");
        return std::string(argv[index]);
      };
      if (option == "--mass") config.mass = std::stod(value());
      else if (option == "--events") config.events = std::stoll(value());
      else if (option == "--cells") config.cells = std::stoi(value());
      else if (option == "--samples") config.samples = std::stoi(value());
      else if (option == "--seed") config.seed = std::stoul(value());
      else if (option == "--selected") config.selected = true;
      else if (option == "--output") config.output = value();
      else throw std::runtime_error("unknown option: " + option);
    }

    ScalarDensity density(config);
    TRandom3 random(config.seed);
    TFoam foam("scalar_foam");
    foam.SetkDim(4);
    foam.SetnCells(config.cells);
    foam.SetnSampl(config.samples);
    foam.SetnBin(8);
    foam.SetOptRej(0);
    foam.SetOptDrive(2);
    foam.SetEvPerBin(25);
    foam.SetChat(0);
    foam.SetRho(&density);
    foam.SetPseRan(&random);
    foam.Initialize();
    std::array<double, 4> point{};
    std::unique_ptr<TFile> output;
    std::unique_ptr<TTree> tree;
    Long64_t event_number = 0;
    double foam_weight = 0.0;
    double mass = config.mass;
    double coupling = config.coupling;
    ScalarEvent event_data;
    bool pass_qe2 = false;
    bool pass_pt = false;
    bool pass_eta = false;
    bool pass_energy = false;
    bool pass_paper_cut = false;
    if (!config.output.empty()) {
      const std::filesystem::path path(config.output);
      if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path());
      output = std::make_unique<TFile>(config.output.c_str(), "RECREATE");
      if (output->IsZombie()) throw std::runtime_error("could not create output file");
      tree = std::make_unique<TTree>("events", "Weighted coherent scalar e Au -> e Au phi events");
      tree->Branch("event", &event_number);
      tree->Branch("foam_weight", &foam_weight);
      tree->Branch("mass", &mass);
      tree->Branch("coupling", &coupling);
      tree->Branch("electron_px", &event_data.electron_px);
      tree->Branch("electron_py", &event_data.electron_py);
      tree->Branch("electron_pz", &event_data.electron_pz);
      tree->Branch("electron_energy", &event_data.electron_energy);
      tree->Branch("electron_pt", &event_data.electron_pt);
      tree->Branch("electron_eta", &event_data.electron_eta);
      tree->Branch("boson_px", &event_data.boson_px);
      tree->Branch("boson_py", &event_data.boson_py);
      tree->Branch("boson_pz", &event_data.boson_pz);
      tree->Branch("boson_energy", &event_data.boson_energy);
      tree->Branch("ion_px", &event_data.ion_px);
      tree->Branch("ion_py", &event_data.ion_py);
      tree->Branch("ion_pz", &event_data.ion_pz);
      tree->Branch("ion_energy", &event_data.ion_energy);
      tree->Branch("Qe2", &event_data.qe2);
      tree->Branch("QA2", &event_data.qa2);
      tree->Branch("pair_mass", &event_data.pair_mass);
      tree->Branch("s_tilde", &event_data.s_tilde);
      tree->Branch("u_tilde", &event_data.u_tilde);
      tree->Branch("t2", &event_data.t2);
      tree->Branch("reduced_amplitude", &event_data.reduced_amplitude);
      tree->Branch("density_pb", &event_data.density_pb);
      tree->Branch("pass_Qe2", &pass_qe2);
      tree->Branch("pass_pt", &pass_pt);
      tree->Branch("pass_eta", &pass_eta);
      tree->Branch("pass_energy", &pass_energy);
      tree->Branch("pass_paper_cut", &pass_paper_cut);
    }
    double sum_weights = 0.0;
    double sum_qe2 = 0.0;
    double sum_qe2_pt = 0.0;
    double sum_qe2_pt_eta = 0.0;
    double sum_all_cuts = 0.0;
    for (long long event = 0; event < config.events; ++event) {
      foam.MakeEvent();
      foam.GetMCvect(point.data());
      if (tree) {
        foam_weight = foam.GetMCwt();
        double event_density = 0.0;
        if (!density.build_event(point.data(), event_data, event_density)) continue;
        const Cut cut = cut_for_mass(config.mass);
        pass_qe2 = event_data.qe2 > cut.qe2_min;
        pass_pt = event_data.electron_pt > cut.pt_min;
        pass_eta = event_data.electron_eta > cut.eta_min && event_data.electron_eta < cut.eta_max;
        pass_energy = event_data.electron_energy < cut.energy_max;
        pass_paper_cut = pass_qe2 && pass_pt && pass_eta && pass_energy;
        sum_weights += foam_weight;
        if (pass_qe2) sum_qe2 += foam_weight;
        if (pass_qe2 && pass_pt) sum_qe2_pt += foam_weight;
        if (pass_qe2 && pass_pt && pass_eta) sum_qe2_pt_eta += foam_weight;
        if (pass_paper_cut) sum_all_cuts += foam_weight;
        event_number = event;
        tree->Fill();
      }
    }
    double sigma = 0.0;
    double error = 0.0;
    foam.GetIntegMC(sigma, error);
    if (output) {
      const double pb_per_weight = sum_weights > 0.0 ? sigma / sum_weights : 0.0;
      const auto xs = [&](double weight) { return pb_per_weight * weight; };
      output->cd();
      tree->Write();
      TParameter<double>("sigma_total_pb", sigma).Write();
      TParameter<double>("sigma_total_error_pb", error).Write();
      TParameter<double>("pb_per_foam_weight", pb_per_weight).Write();
      TParameter<double>("sum_foam_weights", sum_weights).Write();
      TParameter<double>("sigma_after_Qe2_pb", xs(sum_qe2)).Write();
      TParameter<double>("sigma_after_Qe2_pt_pb", xs(sum_qe2_pt)).Write();
      TParameter<double>("sigma_after_Qe2_pt_eta_pb", xs(sum_qe2_pt_eta)).Write();
      TParameter<double>("sigma_paper_cut_pb", xs(sum_all_cuts)).Write();
      std::ostringstream configuration;
      configuration << std::setprecision(12)
                    << "process=scalar;mass_GeV=" << config.mass
                    << ";cut_mass_GeV=" << config.mass
                    << ";coupling=" << config.coupling
                    << ";electron_energy_GeV=" << config.electron_energy
                    << ";ion_energy_per_nucleon_GeV="
                    << config.ion_energy_per_nucleon
                    << ";ion_mass_GeV=" << config.ion_mass
                    << ";A=" << config.mass_number
                    << ";Z=" << config.charge_number
                    << ";events=" << config.events
                    << ";cells=" << config.cells
                    << ";samples=" << config.samples
                    << ";seed=" << config.seed
                    << ";integrate_paper_cut=" << (config.selected ? 1 : 0);
      TNamed("generator_configuration", configuration.str().c_str()).Write();
      tree.reset();
      output->Close();
      std::cout << std::setprecision(12)
                << "sigma_after_Qe2_pb=" << xs(sum_qe2) << "\n"
                << "sigma_after_Qe2_pt_pb=" << xs(sum_qe2_pt) << "\n"
                << "sigma_after_Qe2_pt_eta_pb=" << xs(sum_qe2_pt_eta) << "\n"
                << "sigma_paper_cut_weighted_pb=" << xs(sum_all_cuts) << "\n"
                << "output=" << config.output << "\n";
    }
    std::cout << std::setprecision(12)
              << "mass_GeV=" << config.mass << "\n"
              << "selected=" << (config.selected ? 1 : 0) << "\n"
              << "sigma_pb=" << sigma << "\n"
              << "error_pb=" << error << "\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << "\n";
    return EXIT_FAILURE;
  }
}
