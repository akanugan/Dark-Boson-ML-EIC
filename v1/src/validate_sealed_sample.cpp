#include <TFile.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TTree.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace {

void require_branch(TTree* tree, const char* name, const std::string& path) {
  if (!tree->GetBranch(name)) {
    throw std::runtime_error("missing branch " + std::string(name) +
                             " in " + path);
  }
}

std::unordered_map<std::string, std::string> parse_configuration(
    const std::string& text) {
  std::unordered_map<std::string, std::string> values;
  std::stringstream stream(text);
  std::string item;
  while (std::getline(stream, item, ';')) {
    const auto separator = item.find('=');
    if (separator == std::string::npos || separator == 0 ||
        separator + 1 >= item.size()) {
      throw std::runtime_error("malformed generator_configuration");
    }
    const std::string key = item.substr(0, separator);
    if (!values.emplace(key, item.substr(separator + 1)).second) {
      throw std::runtime_error("duplicate configuration key " + key);
    }
  }
  return values;
}

const std::string& required_value(
    const std::unordered_map<std::string, std::string>& values,
    const std::string& key) {
  const auto found = values.find(key);
  if (found == values.end()) {
    throw std::runtime_error("missing configuration key " + key);
  }
  return found->second;
}

bool close_number(double left, double right) {
  const double scale = std::max({std::abs(left), std::abs(right), 1.0e-6});
  return std::abs(left - right) <= 1.0e-10 * scale + 1.0e-14;
}

void require_number(
    const std::unordered_map<std::string, std::string>& values,
    const std::string& key, double expected) {
  const double observed = std::stod(required_value(values, key));
  if (!std::isfinite(observed) || !close_number(observed, expected)) {
    throw std::runtime_error("configuration mismatch for " + key);
  }
}

void require_integer(
    const std::unordered_map<std::string, std::string>& values,
    const std::string& key, long long expected) {
  if (std::stoll(required_value(values, key)) != expected) {
    throw std::runtime_error("configuration mismatch for " + key);
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 17) {
      throw std::runtime_error(
          "usage: validate_sealed_sample file.root Qe2_min pt_min eta_min "
          "eta_max energy_max photon_expected minimum_entries process "
          "generator_mass cut_mass coupling seed events cells samples");
    }
    const std::string path = argv[1];
    const double qe2_min = std::stod(argv[2]);
    const double pt_min = std::stod(argv[3]);
    const double eta_min = std::stod(argv[4]);
    const double eta_max = std::stod(argv[5]);
    const double energy_max = std::stod(argv[6]);
    const bool photon_expected = std::stoi(argv[7]) != 0;
    const Long64_t minimum_entries = std::stoll(argv[8]);
    const std::string expected_process = argv[9];
    const double expected_mass = std::stod(argv[10]);
    const double expected_cut_mass = std::stod(argv[11]);
    const double expected_coupling = std::stod(argv[12]);
    const long long expected_seed = std::stoll(argv[13]);
    const long long expected_events = std::stoll(argv[14]);
    const long long expected_cells = std::stoll(argv[15]);
    const long long expected_samples = std::stoll(argv[16]);

    TFile file(path.c_str(), "READ");
    if (file.IsZombie()) throw std::runtime_error("cannot open " + path);
    auto* tree = dynamic_cast<TTree*>(file.Get("events"));
    if (!tree) throw std::runtime_error("missing events tree in " + path);
    if (tree->GetEntries() < minimum_entries) {
      throw std::runtime_error("too few stored events in " + path);
    }
    for (const char* branch : {"foam_weight", "Qe2", "QA2", "electron_pt",
                               "electron_eta", "electron_energy",
                               "pass_paper_cut"}) {
      require_branch(tree, branch, path);
    }
    if (photon_expected) {
      require_branch(tree, "photon_miss_probability", path);
      require_branch(tree, "boson_eta", path);
    }

    auto* normalization = dynamic_cast<TParameter<double>*>(
        file.Get("pb_per_foam_weight"));
    auto* cross_section = dynamic_cast<TParameter<double>*>(
        file.Get("sigma_total_pb"));
    auto* configuration = dynamic_cast<TNamed*>(
        file.Get("generator_configuration"));
    if (!normalization || !cross_section || !configuration) {
      throw std::runtime_error("missing required metadata in " + path);
    }
    const auto configuration_values =
        parse_configuration(configuration->GetTitle());
    if (required_value(configuration_values, "process") != expected_process) {
      throw std::runtime_error("configuration mismatch for process");
    }
    require_number(configuration_values, "mass_GeV", expected_mass);
    require_number(configuration_values, "cut_mass_GeV", expected_cut_mass);
    require_number(configuration_values, "coupling", expected_coupling);
    require_number(configuration_values, "electron_energy_GeV", 18.0);
    require_number(configuration_values, "ion_energy_per_nucleon_GeV", 100.0);
    require_number(configuration_values, "ion_mass_GeV", 183.0);
    require_integer(configuration_values, "A", 197);
    require_integer(configuration_values, "Z", 79);
    require_integer(configuration_values, "seed", expected_seed);
    require_integer(configuration_values, "events", expected_events);
    require_integer(configuration_values, "cells", expected_cells);
    require_integer(configuration_values, "samples", expected_samples);
    require_integer(configuration_values, "integrate_paper_cut", 1);
    if (!(normalization->GetVal() > 0.0 &&
          std::isfinite(normalization->GetVal()) &&
          cross_section->GetVal() > 0.0 &&
          std::isfinite(cross_section->GetVal()))) {
      throw std::runtime_error("invalid normalization metadata in " + path);
    }

    double foam_weight = 0.0;
    double qe2 = 0.0;
    double qa2 = 0.0;
    double pt = 0.0;
    double eta = 0.0;
    double energy = 0.0;
    double miss = 1.0;
    double boson_eta = 0.0;
    bool stored_pass = false;
    tree->SetBranchAddress("foam_weight", &foam_weight);
    tree->SetBranchAddress("Qe2", &qe2);
    tree->SetBranchAddress("QA2", &qa2);
    tree->SetBranchAddress("electron_pt", &pt);
    tree->SetBranchAddress("electron_eta", &eta);
    tree->SetBranchAddress("electron_energy", &energy);
    tree->SetBranchAddress("pass_paper_cut", &stored_pass);
    if (photon_expected) {
      tree->SetBranchAddress("photon_miss_probability", &miss);
      tree->SetBranchAddress("boson_eta", &boson_eta);
    }

    long double sum_weight = 0.0L;
    for (Long64_t index = 0; index < tree->GetEntries(); ++index) {
      tree->GetEntry(index);
      if (!(std::isfinite(foam_weight) && foam_weight >= 0.0 &&
            std::isfinite(qe2) && std::isfinite(qa2) && qa2 > 0.0 &&
            std::isfinite(pt) && std::isfinite(eta) &&
            std::isfinite(energy))) {
        throw std::runtime_error("non-finite/invalid event in " + path);
      }
      const bool recomputed_pass =
          qe2 > qe2_min && pt > pt_min && eta > eta_min && eta < eta_max &&
          energy < energy_max;
      if (!stored_pass || !recomputed_pass) {
        throw std::runtime_error("event outside frozen Table-I region in " + path);
      }
      if (photon_expected &&
          !(std::isfinite(miss) && miss >= 0.0 && miss <= 1.0)) {
        throw std::runtime_error("invalid photon miss weight in " + path);
      }
      if (photon_expected) {
        if (!std::isfinite(boson_eta)) {
          throw std::runtime_error("invalid boson eta in " + path);
        }
        const double expected_miss =
            std::abs(boson_eta) > 3.5 ? 1.0 : 1.0e-6;
        if (!close_number(miss, expected_miss)) {
          throw std::runtime_error("photon miss-rule mismatch in " + path);
        }
      }
      sum_weight += static_cast<long double>(foam_weight) *
                    static_cast<long double>(photon_expected ? miss : 1.0);
    }
    if (!(sum_weight > 0.0L)) {
      throw std::runtime_error("zero total event weight in " + path);
    }
    std::cout << "validated " << path << " entries=" << tree->GetEntries()
              << '\n';
    return EXIT_SUCCESS;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return EXIT_FAILURE;
  }
}
