#include <TMVA/MethodBase.h>
#include <TMVA/MethodPDERS.h>
#include <TMVA/Reader.h>

#include <TFile.h>
#include <TParameter.h>
#include <TTree.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <regex>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

// This exporter never fits a model or chooses a selection. It applies a model,
// threshold, and rectangular selection already chosen using validation data.
// Physical photon weights are foam_weight * pb_per_foam_weight * miss; the
// merged refit samples store raw physical pb in foam_weight and normalization 1.
namespace {
constexpr std::size_t kFeatures = 5;
using Row = std::unordered_map<std::string, std::string>;

std::vector<std::string> split_csv(const std::string& line) {
  std::vector<std::string> fields;
  std::stringstream stream(line);
  std::string field;
  while (std::getline(stream, field, ',')) fields.push_back(field);
  if (!line.empty() && line.back() == ',') fields.emplace_back();
  return fields;
}

Row read_selected_row(const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open selection CSV: " + path);
  std::string header, values, extra;
  if (!std::getline(input, header) || !std::getline(input, values))
    throw std::runtime_error("missing selection CSV row: " + path);
  if (!header.empty() && header.back() == '\r') header.pop_back();
  if (!values.empty() && values.back() == '\r') values.pop_back();
  const auto names = split_csv(header), data = split_csv(values);
  if (names.size() != data.size())
    throw std::runtime_error("selection CSV column mismatch: " + path);
  Row row;
  for (std::size_t i = 0; i < names.size(); ++i) {
    if (names[i].empty() || !row.emplace(names[i], data[i]).second)
      throw std::runtime_error("empty or duplicate selection CSV column: " + path);
  }
  while (std::getline(input, extra)) {
    if (extra.find_first_not_of(" \t\r") != std::string::npos)
      throw std::runtime_error("expected exactly one selected CSV row: " + path);
  }
  return row;
}

std::string required_text(const Row& row, const std::string& key) {
  const auto found = row.find(key);
  if (found == row.end() || found->second.empty())
    throw std::runtime_error("missing selection CSV column: " + key);
  return found->second;
}

double parse_number(const std::string& value, const std::string& context) {
  std::size_t used = 0;
  const double result = std::stod(value, &used);
  if (used != value.size() || std::isnan(result))
    throw std::runtime_error("invalid number for " + context);
  return result;
}

double required_number(const Row& row, const std::string& key) {
  return parse_number(required_text(row, key), key);
}

bool close_number(double a, double b) {
  return std::isfinite(a) && std::isfinite(b) &&
         std::abs(a - b) <= 1e-10 * std::max({1.0, std::abs(a), std::abs(b)});
}

struct Box {
  std::array<double, kFeatures> lower{}, upper{};
  std::size_t count = 0;

  bool passes(const std::array<double, kFeatures>& values) const {
    for (std::size_t i = 0; i < count; ++i)
      if (values[i] < lower[i] || values[i] > upper[i]) return false;
    return true;
  }
};

Box read_box(const Row& row, std::size_t count) {
  const std::array<std::string, kFeatures> keys{
      "logQe2", "pt", "eta", "energy", "logQA2"};
  Box box;
  box.count = count;
  for (std::size_t i = 0; i < count; ++i) {
    box.lower[i] = required_number(row, keys[i] + "_min");
    box.upper[i] = required_number(row, keys[i] + "_max");
    if (box.lower[i] > box.upper[i])
      throw std::runtime_error("inverted rectangular bounds: " + keys[i]);
  }
  return box;
}

// Check that the XML belongs to the profile named in the selected CSV; merely
// checking BDT versus PDERS would allow a different fitted profile by mistake.
void check_model_profile(const std::string& path, const std::string& profile) {
  std::ifstream xml(path);
  if (!xml) throw std::runtime_error("cannot open model XML: " + path);
  std::unordered_map<std::string, std::string> options;
  const std::regex option("<Option name=\"([^\"]+)\"[^>]*>([^<]*)</Option>");
  std::string line;
  while (std::getline(xml, line)) {
    std::smatch match;
    if (std::regex_search(line, match, option)) options[match[1]] = match[2];
    if (line.find("</Options>") != std::string::npos) break;
  }
  const auto number = [&](const std::string& key) {
    const auto found = options.find(key);
    if (found == options.end()) throw std::runtime_error("missing model XML option: " + key);
    return parse_number(found->second, "model XML option " + key);
  };
  std::smatch match;
  if (std::regex_match(profile, match, std::regex("depth([0-9]+)(?:_([0-9]+))?"))) {
    const double depth = std::stod(match[1]);
    const double trees = match[2].matched ? std::stod(match[2]) : 400;
    if (!close_number(number("MaxDepth"), depth) || !close_number(number("NTrees"), trees))
      throw std::runtime_error("model XML does not match selected BDT profile: " + profile);
  } else if (std::regex_match(profile, match, std::regex("h([0-9]+)"))) {
    if (!close_number(number("DeltaFrac"), std::stod(match[1]) / 10))
      throw std::runtime_error("model XML does not match selected PDERS profile: " + profile);
  } else {
    throw std::runtime_error("unrecognized selected model profile: " + profile);
  }
}

class Model {
 public:
  Model(const std::string& weights, const std::string& features,
        const std::string& profile) : reader_("!Color:Silent") {
    check_model_profile(weights, profile);
    reader_.AddVariable("log10(Qe2)", &log_qe2_);
    if (features == "electron_qa2")
      reader_.AddVariable("log10(QA2)", &log_t_);
    reader_.AddVariable("electron_pt", &pt_);
    reader_.AddVariable("electron_eta", &eta_);
    reader_.AddVariable("electron_energy", &energy_);
    auto* method = reader_.BookMVA("selection", weights.c_str());
    if (!method) throw std::runtime_error("could not load model: " + weights);
    auto* pders = dynamic_cast<TMVA::MethodPDERS*>(method);
    const bool is_pders = pders != nullptr;
    if (profile.rfind("h", 0) == 0 && !is_pders)
      throw std::runtime_error("selected likelihood profile has non-PDERS XML");
    if (profile.rfind("depth", 0) == 0 && is_pders)
      throw std::runtime_error("selected BDT profile has PDERS XML");
    // ROOT serializes PDERS option strings but requires this refresh to set
    // its mode/kernel enums. This is the same fix used in existing evaluation.
    if (pders) static_cast<TMVA::MethodBase*>(pders)->ProcessSetup();
    method_name_ = is_pders ? "PDERS" : "BDT";
  }

  double score(const std::array<double, kFeatures>& value) {
    log_qe2_ = static_cast<float>(value[0]);
    pt_ = static_cast<float>(value[1]);
    eta_ = static_cast<float>(value[2]);
    energy_ = static_cast<float>(value[3]);
    log_t_ = static_cast<float>(value[4]);
    return reader_.EvaluateMVA("selection");
  }
  const std::string& method_name() const { return method_name_; }

 private:
  float log_qe2_ = 0, log_t_ = 0, pt_ = 0, eta_ = 0, energy_ = 0;
  TMVA::Reader reader_;
  std::string method_name_;
};

struct Summary {
  Long64_t entries = 0, half_entries = 0;
  double sumw = 0, sumw2 = 0, raw_sumw = 0, maximum = 0;
  double model_sumw = 0, cuts_sumw = 0, half_sumw = 0;

  void add(double weight, double raw, bool model, bool cuts, bool half) {
    ++entries;
    sumw += weight;
    sumw2 += weight * weight;
    raw_sumw += raw;
    maximum = std::max(maximum, weight);
    if (model) model_sumw += weight;
    if (cuts) cuts_sumw += weight;
    if (half) { ++half_entries; half_sumw += weight; }
  }
  double neff() const { return sumw2 > 0 ? sumw * sumw / sumw2 : 0; }
  double fraction(double numerator) const { return sumw > 0 ? numerator / sumw : 0; }
};

struct SampleSummary {
  Summary all, central, outside;
  double pb_per_weight = 0;
  std::uint64_t smearing_redraws = 0;
};

template <typename T>
void bind(TTree& tree, const std::string& file, const char* name, T* address) {
  if (!tree.GetBranch(name))
    throw std::runtime_error("missing branch " + std::string(name) + " in " + file);
  tree.SetBranchStatus(name, 1);
  if (tree.SetBranchAddress(name, address) < 0)
    throw std::runtime_error("branch type mismatch " + std::string(name) + " in " + file);
}

SampleSummary export_sample(const std::string& path, const std::string& output,
                            bool photon, Model& model, const Box& box,
                            double threshold, double expected_mass,
                            double t_fraction, std::uint64_t smearing_seed) {
  TFile input(path.c_str(), "READ");
  if (input.IsZombie()) throw std::runtime_error("cannot open ROOT file: " + path);
  auto* tree = dynamic_cast<TTree*>(input.Get("events"));
  if (!tree || tree->GetEntries() == 0)
    throw std::runtime_error("missing or empty events tree: " + path);
  auto* norm = dynamic_cast<TParameter<double>*>(input.Get("pb_per_foam_weight"));
  if (!norm || !std::isfinite(norm->GetVal()) || norm->GetVal() <= 0)
    throw std::runtime_error("missing or invalid pb_per_foam_weight: " + path);
  SampleSummary summary;
  summary.pb_per_weight = norm->GetVal();
  if (photon && !close_number(summary.pb_per_weight, 1.0))
    throw std::runtime_error("merged refit photon normalization must be 1: " + path);
  // Distinct streams for the two samples, but identical streams for different
  // selectors applied with the same seed and event order. The selected models
  // and thresholds stay fixed: this is an assumed-resolution benchmark, not
  // a new detector calibration or a retraining using smeared inputs.
  const std::uint64_t stream_offset = photon ? 0x50484f544f4eULL : 0x5349474e414cULL;
  std::mt19937_64 generator(smearing_seed + stream_offset);
  std::normal_distribution<double> gaussian(0.0, 1.0);

  Long64_t event_id = 0, source_event = 0;
  Int_t stratum = -1;
  double foam = 0, qe2 = 0, t = 0, pt = 0, eta = 0, energy = 0, miss = 1, mass = 0;
  tree->SetBranchStatus("*", 0);
  bind(*tree, path, "event", &event_id);
  bind(*tree, path, "foam_weight", &foam);
  bind(*tree, path, "Qe2", &qe2);
  bind(*tree, path, "QA2", &t);
  bind(*tree, path, "electron_pt", &pt);
  bind(*tree, path, "electron_eta", &eta);
  bind(*tree, path, "electron_energy", &energy);
  bind(*tree, path, photon ? "cut_mass" : "mass", &mass);
  if (photon) {
    bind(*tree, path, "source_event", &source_event);
    bind(*tree, path, "photon_stratum", &stratum);
    bind(*tree, path, "photon_miss_probability", &miss);
  }

  std::ofstream csv(output);
  if (!csv) throw std::runtime_error("cannot write output: " + output);
  csv << "event_id,source_event,photon_stratum,weight,raw_weight,"
         "photon_miss_probability,logQe2,logt,raw_logt,pt,eta,energy,score,"
         "score_half,model_pass,cuts_pass\n" << std::setprecision(17);
  for (Long64_t index = 0; index < tree->GetEntries(); ++index) {
    if (tree->GetEntry(index) <= 0)
      throw std::runtime_error("cannot read ROOT entry in " + path);
    if (!photon) source_event = event_id;
    if (!close_number(mass, expected_mass))
      throw std::runtime_error("sample mass/preselection does not match selected CSV: " + path);
    if (!(std::isfinite(qe2) && qe2 > 0 && std::isfinite(t) && t > 0 &&
          std::isfinite(pt) && pt >= 0 && std::isfinite(eta) &&
          std::isfinite(energy) && energy > 0 && std::isfinite(foam) && foam >= 0))
      throw std::runtime_error("invalid physical event at entry " + std::to_string(index) + " in " + path);
    if (photon && (stratum < 0 || stratum > 1 || !std::isfinite(miss) ||
                   miss <= 0 || miss > 1 || (stratum == 1 && !close_number(miss, 1))))
      throw std::runtime_error("invalid photon stratum/miss at entry " + std::to_string(index));
    double effective_t = t;
    if (t_fraction > 0) {
      double factor = 0;
      do {
        factor = 1.0 + t_fraction * gaussian(generator);
        if (factor <= 0) ++summary.smearing_redraws;
      } while (factor <= 0);
      effective_t = t * factor;
      if (!(std::isfinite(effective_t) && effective_t > 0))
        throw std::runtime_error("invalid smeared t at entry " + std::to_string(index));
    }
    const double raw_logt = std::log10(t);
    const std::array<double, kFeatures> values{
        std::log10(qe2), pt, eta, energy, std::log10(effective_t)};
    const double score = model.score(values);
    const double raw = foam * summary.pb_per_weight;
    const double weight = raw * miss;
    if (!(std::isfinite(score) && std::isfinite(raw) && std::isfinite(weight)))
      throw std::runtime_error("invalid score or physical weight at entry " + std::to_string(index));
    const bool half = score == 0.5;  // Diagnostic proxy, not proof of missing support.
    const bool model_pass = score >= threshold;
    const bool cuts_pass = box.passes(values);
    summary.all.add(weight, raw, model_pass, cuts_pass, half);
    if (photon) (stratum == 0 ? summary.central : summary.outside)
        .add(weight, raw, model_pass, cuts_pass, half);
    csv << event_id << ',' << source_event << ',' << stratum << ',' << weight
        << ',' << raw << ',' << miss << ',' << values[0] << ',' << values[4]
        << ',' << raw_logt << ',' << pt << ',' << eta << ',' << energy << ',' << score << ','
        << half << ',' << model_pass << ',' << cuts_pass << '\n';
  }
  if (!csv) throw std::runtime_error("failed writing output: " + output);
  if (!(summary.all.sumw > 0)) throw std::runtime_error("zero sample weight: " + path);
  if (photon && (summary.central.entries == 0 || summary.outside.entries == 0))
    throw std::runtime_error("merged photon sample must contain both strata: " + path);
  return summary;
}

void write_summary_row(std::ostream& output, const std::string& sample,
                       const std::string& stratum, const Summary& summary,
                       double t_fraction, std::uint64_t smearing_seed,
                       std::uint64_t sample_redraws) {
  output << sample << ',' << stratum << ',' << summary.entries << ','
         << summary.raw_sumw << ',' << summary.sumw << ',' << summary.sumw2
         << ',' << summary.neff() << ',' << summary.fraction(summary.maximum)
         << ',' << summary.model_sumw << ',' << summary.fraction(summary.model_sumw)
         << ',' << summary.cuts_sumw << ',' << summary.fraction(summary.cuts_sumw)
         << ',' << summary.half_entries << ',' << summary.half_sumw << ','
         << summary.fraction(summary.half_sumw) << ',' << t_fraction << ','
         << smearing_seed << ',' << sample_redraws << '\n';
}
}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 10 || argc > 12)
      throw std::runtime_error(
          "usage: export_refit_scores signal.root merged_photon.root weights.xml "
          "selected_model.csv cuts_selected.csv prefix electron|electron_qa2 "
          "photon_xs_pb dis_xs_pb [t_fraction [smearing_seed]]");
    const std::string features = argv[7];
    if (features != "electron" && features != "electron_qa2")
      throw std::runtime_error("feature set must be electron or electron_qa2");
    const double photon_xs = parse_number(argv[8], "photon_xs_pb");
    const double dis_xs = parse_number(argv[9], "dis_xs_pb");
    const double t_fraction = argc >= 11 ? parse_number(argv[10], "t_fraction") : 0.0;
    if (!(std::isfinite(t_fraction) && t_fraction >= 0))
      throw std::runtime_error("t_fraction must be finite and nonnegative");
    std::uint64_t smearing_seed = 20261024;
    if (argc >= 12) {
      const std::string value(argv[11]);
      if (value.empty() || value.find_first_not_of("0123456789") != std::string::npos)
        throw std::runtime_error("smearing_seed must be an unsigned integer");
      std::size_t used = 0;
      smearing_seed = std::stoull(value, &used);
      if (used != value.size()) throw std::runtime_error("invalid smearing_seed");
    }
    if (!(std::isfinite(photon_xs) && photon_xs > 0 &&
          std::isfinite(dis_xs) && dis_xs >= 0))
      throw std::runtime_error("background rates must be finite, photon >0, DIS >=0");
    const Row selected = read_selected_row(argv[4]);
    const Row cuts = read_selected_row(argv[5]);
    for (const Row* row : {&selected, &cuts}) {
      if (required_text(*row, "feature_set") != features)
        throw std::runtime_error("feature-set mismatch among inputs");
      if (!close_number(required_number(*row, "photon_xs_pb"), photon_xs) ||
          !close_number(required_number(*row, "dis_xs_pb"), dis_xs))
        throw std::runtime_error("background-rate mismatch among inputs");
    }
    if (required_text(selected, "signal_type") != required_text(cuts, "signal_type") ||
        !close_number(required_number(selected, "mass_GeV"), required_number(cuts, "mass_GeV")))
      throw std::runtime_error("signal type/mass mismatch among selected inputs");
    const double threshold = required_number(selected, "validation_threshold");
    const double expected_mass = required_number(selected, "mass_GeV");
    if (!(std::isfinite(expected_mass) && expected_mass > 0))
      throw std::runtime_error("selected signal mass must be positive and finite");
    const Box box = read_box(cuts, features == "electron" ? 4 : 5);
    const std::filesystem::path prefix(argv[6]);
    if (prefix.has_parent_path()) std::filesystem::create_directories(prefix.parent_path());
    Model model(argv[3], features, required_text(selected, "model_profile"));
    const auto signal = export_sample(argv[1], prefix.string() + "_signal.csv",
                                      false, model, box, threshold, expected_mass,
                                      t_fraction, smearing_seed);
    const auto photon = export_sample(argv[2], prefix.string() + "_photon.csv",
                                      true, model, box, threshold, expected_mass,
                                      t_fraction, smearing_seed);
    std::ofstream support(prefix.string() + "_support.csv");
    if (!support) throw std::runtime_error("cannot write support summary");
    support << "sample,stratum,entries,raw_sumw_pb,sumw_pb,sumw2_pb2,neff,"
               "maximum_weight_fraction,model_pass_sumw_pb,model_efficiency,"
               "cuts_pass_sumw_pb,cuts_efficiency,score_half_entries,"
               "score_half_sumw_pb,score_half_weight_fraction,t_fraction,"
               "smearing_seed,sample_smearing_redraws\n" << std::setprecision(17);
    write_summary_row(support, "signal", "all", signal.all, t_fraction,
                       smearing_seed, signal.smearing_redraws);
    write_summary_row(support, "photon", "all", photon.all, t_fraction,
                       smearing_seed, photon.smearing_redraws);
    write_summary_row(support, "photon", "central", photon.central, t_fraction,
                       smearing_seed, photon.smearing_redraws);
    write_summary_row(support, "photon", "outside", photon.outside, t_fraction,
                       smearing_seed, photon.smearing_redraws);
    const double model_signal_eff = signal.all.fraction(signal.all.model_sumw);
    const double cuts_signal_eff = signal.all.fraction(signal.all.cuts_sumw);
    const double model_photon_eff = photon.all.fraction(photon.all.model_sumw);
    const double cuts_photon_eff = photon.all.fraction(photon.all.cuts_sumw);
    const auto rz = [&](double signal_eff, double photon_eff) {
      const double remaining = photon_xs * photon_eff + dis_xs;
      return remaining > 0 ? signal_eff * std::sqrt((photon_xs + dis_xs) / remaining)
                           : std::numeric_limits<double>::quiet_NaN();
    };
    const double model_rz = rz(model_signal_eff, model_photon_eff);
    const double cuts_rz = rz(cuts_signal_eff, cuts_photon_eff);
    std::ofstream metrics(prefix.string() + "_metrics.csv");
    if (!metrics) throw std::runtime_error("cannot write metrics summary");
    metrics << "method,feature_set,signal_type,mass_GeV,model_profile,threshold,"
               "photon_xs_pb,dis_xs_pb,signal_sample_sumw_pb,photon_sample_sumw_pb,"
               "model_signal_efficiency,model_photon_efficiency,model_RZ,"
               "cuts_signal_efficiency,cuts_photon_efficiency,cuts_RZ,RZ_ratio,"
               "t_fraction,smearing_seed,evaluation_kind\n"
            << std::setprecision(17) << model.method_name() << ',' << features << ','
            << required_text(selected, "signal_type") << ',' << required_text(selected, "mass_GeV")
            << ',' << required_text(selected, "model_profile") << ',' << threshold << ','
            << photon_xs << ',' << dis_xs << ',' << signal.all.sumw << ',' << photon.all.sumw
            << ',' << model_signal_eff << ',' << model_photon_eff << ',' << model_rz
            << ',' << cuts_signal_eff << ',' << cuts_photon_eff << ',' << cuts_rz << ','
            << (cuts_rz > 0 ? model_rz / cuts_rz : std::numeric_limits<double>::quiet_NaN())
            << ',' << t_fraction << ',' << smearing_seed << ','
            << (t_fraction > 0 ? "fixed_selectors_assumed_resolution" : "nominal_fixed_selectors") << '\n';
    if (!support || !metrics) throw std::runtime_error("failed writing summaries");
    std::cout << std::setprecision(10) << "exported " << model.method_name() << ' '
              << features << ": signal=" << signal.all.entries << " photon=" << photon.all.entries
              << " outside_score_half_fraction=" << photon.outside.fraction(photon.outside.half_sumw)
              << " RZ_ratio=" << model_rz / cuts_rz << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
