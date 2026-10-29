#include <TBranch.h>
#include <TFile.h>
#include <TLeaf.h>
#include <TNamed.h>
#include <TObjArray.h>
#include <TParameter.h>
#include <TTree.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <unistd.h>

namespace fs = std::filesystem;

namespace {

using Configuration = std::map<std::string, std::string>;

Configuration configuration(TFile& file) {
  const auto* named = dynamic_cast<TNamed*>(file.Get("generator_configuration"));
  if (!named) throw std::runtime_error("missing generator_configuration");
  Configuration result;
  std::istringstream input(named->GetTitle());
  std::string item;
  while (std::getline(input, item, ';')) {
    const auto separator = item.find('=');
    if (separator == std::string::npos) continue;
    const auto key = item.substr(0, separator);
    if (!result.emplace(key, item.substr(separator + 1)).second)
      throw std::runtime_error("duplicate configuration key " + key);
  }
  return result;
}

const std::string& require(const Configuration& config, const std::string& key) {
  const auto found = config.find(key);
  if (found == config.end()) throw std::runtime_error("missing configuration key " + key);
  return found->second;
}

double parameter(TFile& file, const char* name) {
  const auto* object = dynamic_cast<TParameter<double>*>(file.Get(name));
  if (!object || !std::isfinite(object->GetVal()))
    throw std::runtime_error(std::string("missing or invalid parameter ") + name);
  return object->GetVal();
}

bool close(double actual, double expected, double tolerance = 2e-9) {
  return std::abs(actual - expected) <=
         tolerance * std::max({1e-300, std::abs(actual), std::abs(expected)});
}

struct Cut {
  double mass, qe2, pt, eta_min, eta_max, energy_max;
};

const Cut& paper_cut(double mass) {
  static const std::array<Cut, 11> cuts = {{{.01, std::pow(10., -.7), 1.1, -3.5, -1.5, 10.},
      {.032, std::pow(10., -.7), 1.1, -3.5, -1.5, 10.},
      {.1, std::pow(10., -.7), 1.1, -3.5, -1.5, 10.},
      {.316, std::pow(10., -.7), 1.1, -3.5, -1.5, 10.},
      {1., std::pow(10., .2), 1.3, -3.5, 2., 10.},
      {1.585, std::pow(10., .5), 1.3, -3., 2., 10.},
      {2.512, std::pow(10., .8), 1.3, -2.5, 2.5, 10.},
      {3.981, std::pow(10., 1.2), 1.3, -2.5, 1., 10.},
      {5., std::pow(10., 1.4), 1.3, -3., 1., 10.},
      {6.31, std::pow(10., 1.5), 1.3, -2., 3.5, 10.},
      {10., std::pow(10., 1.5), 1.3, -1.5, 3., 10.}}};
  const auto found = std::find_if(cuts.begin(), cuts.end(), [mass](const Cut& c) {
    return close(c.mass, mass, 1e-8);
  });
  if (found == cuts.end()) throw std::runtime_error("unsupported preselection mass");
  return *found;
}

struct Source {
  std::string path;
  std::unique_ptr<TFile> file;
  TTree* tree = nullptr;
  Configuration config;
  Long64_t attempts = 0;
  Long64_t entries = 0;
  double normalization = 0.;
  double sigma = 0.;
  double error = 0.;
  double sum_raw = 0.;
  double sum_effective = 0.;
};

Source open_source(const fs::path& path, const std::string& region) {
  Source source;
  source.path = fs::canonical(path).string();
  source.file.reset(TFile::Open(source.path.c_str(), "READ"));
  if (!source.file || source.file->IsZombie()) throw std::runtime_error("cannot open " + source.path);
  source.tree = dynamic_cast<TTree*>(source.file->Get("events"));
  if (!source.tree || source.tree->GetEntries() < 1) throw std::runtime_error("empty or missing events tree");
  source.config = configuration(*source.file);
  if (require(source.config, "photon_region") != region)
    throw std::runtime_error("incorrect photon region in " + source.path);
  if (require(source.config, "process") != "vector" ||
      require(source.config, "integrate_paper_cut") != "1")
    throw std::runtime_error("source must be a photon proxy integrated over the paper cuts");
  source.attempts = std::stoll(require(source.config, "events"));
  source.entries = source.tree->GetEntries();
  if (source.attempts < source.entries || source.attempts < 1)
    throw std::runtime_error("invalid source attempted-event count");
  source.normalization = parameter(*source.file, "pb_per_foam_weight");
  source.sigma = parameter(*source.file, "sigma_total_pb");
  source.error = parameter(*source.file, "sigma_total_error_pb");
  if (!(source.normalization > 0. && source.sigma > 0. && source.error >= 0.))
    throw std::runtime_error("invalid source normalization or integral");
  for (const char* name : {"event", "foam_weight", "photon_miss_probability", "boson_eta",
                          "pass_paper_cut", "Qe2", "electron_pt", "electron_eta",
                          "electron_energy", "cut_mass", "mass", "coupling"}) {
    if (!source.tree->GetLeaf(name)) throw std::runtime_error(std::string("missing leaf ") + name);
  }
  if (source.tree->GetBranch("photon_stratum") || source.tree->GetBranch("source_event"))
    throw std::runtime_error("source already contains stratum identifiers");
  return source;
}

void check_compatible(const Source& central, const Source& outside) {
  auto* first = central.tree->GetListOfBranches();
  auto* second = outside.tree->GetListOfBranches();
  if (first->GetEntries() != second->GetEntries()) throw std::runtime_error("source branch counts differ");
  for (int index = 0; index < first->GetEntries(); ++index) {
    auto* branch = dynamic_cast<TBranch*>(first->At(index));
    auto* counterpart = outside.tree->GetBranch(branch->GetName());
    if (!counterpart || std::string(branch->GetTitle()) != counterpart->GetTitle())
      throw std::runtime_error("source schemas differ at " + std::string(branch->GetName()));
  }
  for (const char* key : {"mass_GeV", "cut_mass_GeV", "coupling", "electron_energy_GeV",
                           "ion_energy_per_nucleon_GeV", "ion_mass_GeV", "A", "Z", "sqrt_s_GeV"}) {
    if (!close(std::stod(require(central.config, key)), std::stod(require(outside.config, key))))
      throw std::runtime_error(std::string("incompatible source physics: ") + key);
  }
  const auto& central_seed = require(central.config, "seed");
  const auto& outside_seed = require(outside.config, "seed");
  if (central_seed == outside_seed) throw std::runtime_error("source integration seeds must be independent");
}

std::string escaped(const std::string& input) {
  std::ostringstream output;
  output << std::quoted(input);
  return output.str();
}

template <class T>
void write_parameter(const char* name, T value) { TParameter<T>(name, value).Write(); }

}  // namespace

int main(int argc, char** argv) {
  fs::path temporary;
  try {
    if (argc < 4 || argc > 5)
      throw std::runtime_error("usage: merge_photon_strata central.root outside.root output.root [epsilon=1e-6]");
    const double epsilon = argc == 5 ? std::stod(argv[4]) : 1e-6;
    if (!(epsilon > 0. && epsilon <= 1. && std::isfinite(epsilon)))
      throw std::runtime_error("epsilon must lie in (0,1]");
    auto central = open_source(argv[1], "central");
    auto outside = open_source(argv[2], "outside");
    if (central.path == outside.path) throw std::runtime_error("source paths must differ");
    check_compatible(central, outside);
    const fs::path destination = fs::absolute(argv[3]);
    if (fs::exists(destination)) throw std::runtime_error("output already exists: " + destination.string());
    fs::create_directories(destination.parent_path());
    temporary = destination.string() + ".tmp." + std::to_string(getpid());
    if (fs::exists(temporary)) throw std::runtime_error("temporary output already exists");

    double foam_weight = 0., miss = 0.;
    Long64_t original_event = 0, source_event = 0;
    int stratum = 0;
    const Cut& cut = paper_cut(std::stod(require(central.config, "cut_mass_GeV")));
    TFile output(temporary.c_str(), "CREATE");
    if (output.IsZombie()) throw std::runtime_error("cannot create temporary output");
    TTree* merged = nullptr;

    for (Source* source : {&central, &outside}) {
      source->tree->SetBranchAddress("foam_weight", &foam_weight);
      source->tree->SetBranchAddress("photon_miss_probability", &miss);
      source->tree->SetBranchAddress("event", &original_event);
      if (source->tree->GetEntry(0) <= 0) throw std::runtime_error("cannot initialize source branch buffers");
      output.cd();
      if (!merged) {
        merged = source->tree->CloneTree(0);
        if (!merged) throw std::runtime_error("CloneTree failed");
        merged->SetDirectory(&output);
        merged->SetTitle("Stratified photon mixture; foam_weight is raw physical pb per event");
        merged->Branch("photon_stratum", &stratum);
        merged->Branch("source_event", &source_event);
      } else {
        source->tree->CopyAddresses(merged);
      }
      const int component = source == &central ? 0 : 1;
      Long64_t previous_event = -1;
      for (Long64_t index = 0; index < source->entries; ++index) {
        if (source->tree->GetEntry(index) <= 0) throw std::runtime_error("failed to read source event");
        for (int leaf_index = 0; leaf_index < source->tree->GetListOfLeaves()->GetEntries(); ++leaf_index) {
          auto* leaf = static_cast<TLeaf*>(source->tree->GetListOfLeaves()->At(leaf_index));
          if (!std::isfinite(leaf->GetValue()))
            throw std::runtime_error("nonfinite source value: " + std::string(leaf->GetName()));
        }
        if (!(foam_weight >= 0.) || original_event < 0 || original_event >= source->attempts ||
            original_event <= previous_event)
          throw std::runtime_error("invalid source weight or event identifier");
        previous_event = original_event;
        const auto value = [&](const char* name) { return source->tree->GetLeaf(name)->GetValue(); };
        const bool is_outside = std::abs(value("boson_eta")) > 3.5;
        if (is_outside != (component == 1)) throw std::runtime_error("source event falls in wrong photon region");
        if (!(value("pass_paper_cut") != 0. && value("Qe2") > cut.qe2 &&
              value("electron_pt") > cut.pt && value("electron_eta") > cut.eta_min &&
              value("electron_eta") < cut.eta_max && value("electron_energy") < cut.energy_max &&
              close(value("cut_mass"), cut.mass)))
          throw std::runtime_error("source event fails expected preselection");
        if (!close(value("mass"), std::stod(require(source->config, "mass_GeV"))) ||
            !close(value("coupling"), std::stod(require(source->config, "coupling"))))
          throw std::runtime_error("source event disagrees with physics metadata");
        foam_weight *= source->normalization;
        miss = component == 0 ? epsilon : 1.;
        stratum = component;
        source_event = original_event;
        source->sum_raw += foam_weight;
        source->sum_effective += foam_weight * miss;
        if (merged->Fill() < 0) throw std::runtime_error("failed to write merged event");
      }
      if (!close(source->sum_raw, source->sigma))
        throw std::runtime_error("source event sum disagrees with integrated cross section");
    }

    const double raw_sigma = central.sigma + outside.sigma;
    const double effective_sigma = epsilon * central.sigma + outside.sigma;
    if (!close(central.sum_effective + outside.sum_effective, effective_sigma))
      throw std::runtime_error("merged effective cross section failed validation");
    output.cd();
    merged->Write();
    write_parameter("pb_per_foam_weight", 1.);
    write_parameter("sigma_total_pb", raw_sigma);
    write_parameter("sigma_total_error_pb", std::hypot(central.error, outside.error));
    write_parameter("sigma_paper_cut_pb", raw_sigma);
    write_parameter("sum_foam_weights", central.sum_raw + outside.sum_raw);
    write_parameter("accepted_events", central.entries + outside.entries);
    write_parameter("source_attempts", central.attempts + outside.attempts);
    write_parameter("source_attempts_central", central.attempts);
    write_parameter("source_attempts_outside", outside.attempts);
    write_parameter("source_entries_central", central.entries);
    write_parameter("source_entries_outside", outside.entries);
    write_parameter("sigma_central_pb", central.sigma);
    write_parameter("sigma_outside_pb", outside.sigma);
    write_parameter("sigma_central_error_pb", central.error);
    write_parameter("sigma_outside_error_pb", outside.error);
    write_parameter("epsilon_central", epsilon);
    write_parameter("effective_cross_section_pb", effective_sigma);
    write_parameter("effective_cross_section_error_pb", std::hypot(epsilon * central.error, outside.error));
    std::ostringstream config;
    config << std::setprecision(17) << "process=photon_mixture;mass_GeV="
           << require(central.config, "mass_GeV") << ";cut_mass_GeV=" << cut.mass
           << ";photon_region=mixture;events=" << central.attempts + outside.attempts
           << ";epsilon_central=" << epsilon << ";outside_miss_probability=1;integrate_paper_cut=1"
           << ";weight_convention=foam_weight_is_raw_pb;pb_per_foam_weight=1";
    TNamed("generator_configuration", config.str().c_str()).Write();
    std::ostringstream provenance;
    provenance << std::setprecision(17)
               << "{\"central_path\":" << escaped(central.path)
               << ",\"outside_path\":" << escaped(outside.path)
               << ",\"central_configuration\":" << escaped(dynamic_cast<TNamed*>(central.file->Get("generator_configuration"))->GetTitle())
               << ",\"outside_configuration\":" << escaped(dynamic_cast<TNamed*>(outside.file->Get("generator_configuration"))->GetTitle())
               << ",\"epsilon\":" << epsilon
               << ",\"weight_formula\":\"merged foam_weight=source foam_weight*source pb_per_foam_weight; effective weight=merged foam_weight*photon_miss_probability\""
               << ",\"photon_stratum\":\"0=central,1=outside\",\"source_event\":\"original source attempted-event identifier\"}";
    TNamed("photon_strata_provenance", provenance.str().c_str()).Write();
    output.Close();
    if (output.TestBit(TFile::kWriteError)) throw std::runtime_error("ROOT reported an output write error");
    {
      TFile check(temporary.c_str(), "READ");
      auto* tree = dynamic_cast<TTree*>(check.Get("events"));
      if (check.IsZombie() || !tree || tree->GetEntries() != central.entries + outside.entries ||
          !tree->GetBranch("photon_stratum") || !tree->GetBranch("source_event") ||
          !close(parameter(check, "effective_cross_section_pb"), effective_sigma))
        throw std::runtime_error("closed-output validation failed");
    }
    // link() refuses to overwrite an output created concurrently; the temporary file
    // and final output are on the same filesystem and contain identical closed bytes.
    if (::link(temporary.c_str(), destination.c_str()) != 0)
      throw std::runtime_error("atomic output publication failed (destination may now exist)");
    fs::remove(temporary);
    temporary.clear();
    std::cout << std::setprecision(15)
              << "central_entries=" << central.entries << '\n'
              << "outside_entries=" << outside.entries << '\n'
              << "central_attempts=" << central.attempts << '\n'
              << "outside_attempts=" << outside.attempts << '\n'
              << "sigma_central_pb=" << central.sigma << '\n'
              << "sigma_outside_pb=" << outside.sigma << '\n'
              << "epsilon_central=" << epsilon << '\n'
              << "effective_cross_section_pb=" << effective_sigma << '\n'
              << "output=" << destination << '\n';
    return 0;
  } catch (const std::exception& error) {
    if (!temporary.empty()) { std::error_code ignored; fs::remove(temporary, ignored); }
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
