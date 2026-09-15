#include <TMVA/Reader.h>

#include <TFile.h>
#include <TParameter.h>
#include <TTree.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

constexpr std::size_t kMaximumFeatures = 5;

struct Event {
  std::array<double, kMaximumFeatures> value{};
  double score = 0.0;
  double weight = 0.0;
  bool bdt_pass = false;
  bool box_pass = false;
};

struct Box {
  std::array<double, kMaximumFeatures> lower{};
  std::array<double, kMaximumFeatures> upper{};
};

struct SelectionResult {
  double signal_efficiency = 0.0;
  double background_efficiency = 0.0;
  double improvement = 0.0;
};

struct Comparison {
  SelectionResult bdt;
  SelectionResult box;
  double ratio = std::numeric_limits<double>::quiet_NaN();
  double log_ratio = std::numeric_limits<double>::quiet_NaN();
  double coupling_advantage = std::numeric_limits<double>::quiet_NaN();
};

struct WeightSummary {
  double sum = 0.0;
  double sum_squared = 0.0;
  double effective_events = 0.0;
  double maximum_fraction = 0.0;
};

std::vector<std::string> split_csv(const std::string& line) {
  std::vector<std::string> fields;
  std::stringstream input(line);
  std::string field;
  while (std::getline(input, field, ',')) fields.push_back(field);
  return fields;
}

std::unordered_map<std::string, std::string> read_first_row(
    const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path);
  std::string header_line;
  std::string value_line;
  if (!std::getline(input, header_line) || !std::getline(input, value_line)) {
    throw std::runtime_error("missing CSV row in " + path);
  }
  const auto headers = split_csv(header_line);
  const auto values = split_csv(value_line);
  if (headers.size() != values.size()) {
    throw std::runtime_error("CSV column mismatch in " + path);
  }
  std::unordered_map<std::string, std::string> row;
  for (std::size_t index = 0; index < headers.size(); ++index) {
    row[headers[index]] = values[index];
  }
  return row;
}

double required_number(const std::unordered_map<std::string, std::string>& row,
                       const std::string& name) {
  const auto found = row.find(name);
  if (found == row.end()) throw std::runtime_error("missing column " + name);
  if (found->second == "inf") return std::numeric_limits<double>::infinity();
  if (found->second == "-inf") return -std::numeric_limits<double>::infinity();
  return std::stod(found->second);
}

std::string required_text(
    const std::unordered_map<std::string, std::string>& row,
    const std::string& name) {
  const auto found = row.find(name);
  if (found == row.end() || found->second.empty()) {
    throw std::runtime_error("missing column " + name);
  }
  return found->second;
}

bool close_number(double left, double right) {
  const double scale = std::max({1.0, std::abs(left), std::abs(right)});
  return std::abs(left - right) <= 1.0e-10 * scale;
}

Box read_box(const std::string& path, std::size_t feature_count) {
  const auto row = read_first_row(path);
  Box box;
  box.lower.fill(-std::numeric_limits<double>::infinity());
  box.upper.fill(std::numeric_limits<double>::infinity());
  const std::array<std::pair<std::string, std::string>, kMaximumFeatures>
      columns{{
          {"logQe2_min", "logQe2_max"},
          {"pt_min", "pt_max"},
          {"eta_min", "eta_max"},
          {"energy_min", "energy_max"},
          {"logQA2_min", "logQA2_max"},
      }};
  for (std::size_t feature = 0; feature < feature_count; ++feature) {
    box.lower[feature] = required_number(row, columns[feature].first);
    box.upper[feature] = required_number(row, columns[feature].second);
  }
  return box;
}

bool passes_box(const Event& event, const Box& box,
                std::size_t feature_count) {
  for (std::size_t feature = 0; feature < feature_count; ++feature) {
    if (event.value[feature] < box.lower[feature] ||
        event.value[feature] > box.upper[feature]) {
      return false;
    }
  }
  return true;
}

std::vector<Event> evaluate_tree(const std::string& path,
                                 const std::string& weights_file,
                                 const std::string& feature_set,
                                 bool photon, double threshold,
                                 const Box& box) {
  TFile file(path.c_str(), "READ");
  if (file.IsZombie()) throw std::runtime_error("cannot open " + path);
  auto* tree = dynamic_cast<TTree*>(file.Get("events"));
  if (!tree) throw std::runtime_error("missing events tree in " + path);
  for (const char* branch : {"foam_weight", "Qe2", "QA2", "electron_pt",
                             "electron_eta", "electron_energy"}) {
    if (!tree->GetBranch(branch)) {
      throw std::runtime_error("missing branch " + std::string(branch) +
                               " in " + path);
    }
  }
  if (photon && !tree->GetBranch("photon_miss_probability")) {
    throw std::runtime_error("missing photon_miss_probability in " + path);
  }

  double foam_weight = 0.0;
  double miss = 1.0;
  double qe2 = 0.0;
  double qa2 = 0.0;
  double pt_value = 0.0;
  double eta_value = 0.0;
  double energy_value = 0.0;
  tree->SetBranchAddress("foam_weight", &foam_weight);
  tree->SetBranchAddress("Qe2", &qe2);
  tree->SetBranchAddress("QA2", &qa2);
  tree->SetBranchAddress("electron_pt", &pt_value);
  tree->SetBranchAddress("electron_eta", &eta_value);
  tree->SetBranchAddress("electron_energy", &energy_value);
  if (photon) tree->SetBranchAddress("photon_miss_probability", &miss);
  auto* normalization = dynamic_cast<TParameter<double>*>(
      file.Get("pb_per_foam_weight"));
  if (!normalization) {
    throw std::runtime_error("missing pb_per_foam_weight in " + path);
  }
  const double pb_per_weight = normalization->GetVal();
  if (!(pb_per_weight > 0.0 && std::isfinite(pb_per_weight))) {
    throw std::runtime_error("invalid pb_per_foam_weight in " + path);
  }

  float log_qe2 = 0.0F;
  float log_qa2 = 0.0F;
  float pt = 0.0F;
  float eta = 0.0F;
  float energy = 0.0F;
  TMVA::Reader reader("!Color:!Silent");
  reader.AddVariable("log10(Qe2)", &log_qe2);
  if (feature_set == "electron_qa2") {
    reader.AddVariable("log10(QA2)", &log_qa2);
  }
  reader.AddVariable("electron_pt", &pt);
  reader.AddVariable("electron_eta", &eta);
  reader.AddVariable("electron_energy", &energy);
  reader.BookMVA("BDTG", weights_file.c_str());

  const std::size_t feature_count = feature_set == "electron" ? 4 : 5;
  std::vector<Event> events;
  events.reserve(static_cast<std::size_t>(tree->GetEntries()));
  for (Long64_t index = 0; index < tree->GetEntries(); ++index) {
    tree->GetEntry(index);
    Event event;
    event.value[0] = std::log10(std::max(qe2, 1.0e-30));
    event.value[1] = pt_value;
    event.value[2] = eta_value;
    event.value[3] = energy_value;
    event.value[4] = std::log10(std::max(qa2, 1.0e-30));
    log_qe2 = static_cast<float>(event.value[0]);
    pt = static_cast<float>(pt_value);
    eta = static_cast<float>(eta_value);
    energy = static_cast<float>(energy_value);
    log_qa2 = static_cast<float>(event.value[4]);
    event.score = reader.EvaluateMVA("BDTG");
    event.weight = foam_weight * pb_per_weight * (photon ? miss : 1.0);
    if (!(event.weight >= 0.0 && std::isfinite(event.weight) &&
          std::isfinite(event.score))) {
      throw std::runtime_error("invalid event weight/score in " + path);
    }
    event.bdt_pass = event.score >= threshold;
    event.box_pass = passes_box(event, box, feature_count);
    events.push_back(event);
  }
  return events;
}

SelectionResult selection_result(const std::vector<Event>& signal,
                                 const std::vector<Event>& background,
                                 bool use_bdt, double photon_xs,
                                 double dis_xs) {
  double signal_total = 0.0;
  double signal_pass = 0.0;
  double background_total = 0.0;
  double background_pass = 0.0;
  for (const auto& event : signal) {
    signal_total += event.weight;
    if (use_bdt ? event.bdt_pass : event.box_pass) {
      signal_pass += event.weight;
    }
  }
  for (const auto& event : background) {
    background_total += event.weight;
    if (use_bdt ? event.bdt_pass : event.box_pass) {
      background_pass += event.weight;
    }
  }
  SelectionResult result;
  if (!(signal_total > 0.0 && background_total > 0.0)) return result;
  result.signal_efficiency = signal_pass / signal_total;
  result.background_efficiency = background_pass / background_total;
  const double baseline = photon_xs + dis_xs;
  const double remaining = photon_xs * result.background_efficiency + dis_xs;
  if (baseline > 0.0 && remaining > 0.0) {
    result.improvement =
        result.signal_efficiency * std::sqrt(baseline / remaining);
  }
  return result;
}

Comparison compare(const std::vector<Event>& signal,
                   const std::vector<Event>& background,
                   double photon_xs, double dis_xs) {
  Comparison result;
  result.bdt = selection_result(signal, background, true,
                                photon_xs, dis_xs);
  result.box = selection_result(signal, background, false,
                                photon_xs, dis_xs);
  if (result.bdt.improvement > 0.0 && result.box.improvement > 0.0) {
    result.ratio = result.bdt.improvement / result.box.improvement;
    result.log_ratio = std::log(result.ratio);
    result.coupling_advantage =
        1.0 - std::sqrt(result.box.improvement / result.bdt.improvement);
  }
  return result;
}

WeightSummary summarize_weights(const std::vector<Event>& events) {
  WeightSummary result;
  double maximum = 0.0;
  for (const auto& event : events) {
    result.sum += event.weight;
    result.sum_squared += event.weight * event.weight;
    maximum = std::max(maximum, event.weight);
  }
  if (result.sum_squared > 0.0) {
    result.effective_events =
        result.sum * result.sum / result.sum_squared;
  }
  if (result.sum > 0.0) result.maximum_fraction = maximum / result.sum;
  return result;
}

double quantile(std::vector<double> values, double probability) {
  if (values.empty()) return 0.0;
  std::sort(values.begin(), values.end());
  const double position = probability * static_cast<double>(values.size() - 1);
  const std::size_t lower = static_cast<std::size_t>(std::floor(position));
  const std::size_t upper = static_cast<std::size_t>(std::ceil(position));
  const double fraction = position - static_cast<double>(lower);
  return values[lower] * (1.0 - fraction) + values[upper] * fraction;
}

std::vector<Event> bootstrap_sample(const std::vector<Event>& source,
                                    std::mt19937& generator) {
  std::uniform_int_distribution<std::size_t> pick(0, source.size() - 1);
  std::vector<Event> result;
  result.reserve(source.size());
  for (std::size_t index = 0; index < source.size(); ++index) {
    result.push_back(source[pick(generator)]);
  }
  return result;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 10 || argc > 12) {
      throw std::runtime_error(
          "usage: evaluate_fair_model signal_test.root background_test.root "
          "weights.xml model_metrics.csv box_metrics.csv output.csv "
          "electron|electron_qa2 photon_xs dis_xs [bootstrap_replicates] "
          "[bootstrap_seed]");
    }
    const std::string feature_set = argv[7];
    if (feature_set != "electron" && feature_set != "electron_qa2") {
      throw std::runtime_error("feature set must be electron or electron_qa2");
    }
    const double photon_xs = std::stod(argv[8]);
    const double dis_xs = std::stod(argv[9]);
    const std::size_t bootstrap_replicates = argc >= 11
        ? static_cast<std::size_t>(std::stoul(argv[10])) : 2000;
    const unsigned int bootstrap_seed = argc >= 12
        ? static_cast<unsigned int>(std::stoul(argv[11])) : 24681357U;
    if (bootstrap_replicates < 500) {
      throw std::runtime_error("bootstrap_replicates must be >=500");
    }

    const auto model_row = read_first_row(argv[4]);
    const auto box_row = read_first_row(argv[5]);
    if (required_text(model_row, "feature_set") != feature_set ||
        required_text(box_row, "feature_set") != feature_set) {
      throw std::runtime_error("feature-set mismatch among inputs");
    }
    for (const auto& row : {model_row, box_row}) {
      if (!close_number(required_number(row, "photon_xs_pb"), photon_xs) ||
          !close_number(required_number(row, "dis_xs_pb"), dis_xs)) {
        throw std::runtime_error("background-rate mismatch among inputs");
      }
    }
    const double threshold = required_number(model_row, "validation_threshold");
    const std::size_t feature_count = feature_set == "electron" ? 4 : 5;
    const Box box = read_box(argv[5], feature_count);
    const auto signal = evaluate_tree(argv[1], argv[3], feature_set,
                                      false, threshold, box);
    const auto background = evaluate_tree(argv[2], argv[3], feature_set,
                                          true, threshold, box);
    const Comparison nominal = compare(signal, background, photon_xs, dis_xs);
    if (!(nominal.ratio > 0.0 && std::isfinite(nominal.ratio) &&
          std::isfinite(nominal.coupling_advantage))) {
      throw std::runtime_error("undefined nominal BDT/box comparison");
    }
    const WeightSummary signal_weights = summarize_weights(signal);
    const WeightSummary background_weights = summarize_weights(background);

    std::mt19937 generator(bootstrap_seed);
    std::vector<double> ratios;
    std::vector<double> log_ratios;
    std::vector<double> coupling_advantages;
    ratios.reserve(bootstrap_replicates);
    log_ratios.reserve(bootstrap_replicates);
    coupling_advantages.reserve(bootstrap_replicates);
    std::size_t invalid_bootstrap_replicates = 0;
    for (std::size_t replicate = 0; replicate < bootstrap_replicates;
         ++replicate) {
      const auto signal_bootstrap = bootstrap_sample(signal, generator);
      const auto background_bootstrap = bootstrap_sample(background, generator);
      const Comparison result = compare(signal_bootstrap, background_bootstrap,
                                        photon_xs, dis_xs);
      if (!(result.ratio > 0.0 && std::isfinite(result.ratio) &&
            std::isfinite(result.log_ratio) &&
            std::isfinite(result.coupling_advantage))) {
        ++invalid_bootstrap_replicates;
        continue;
      }
      ratios.push_back(result.ratio);
      log_ratios.push_back(result.log_ratio);
      coupling_advantages.push_back(result.coupling_advantage);
    }
    if ((feature_set == "electron" && invalid_bootstrap_replicates != 0) ||
        ratios.size() < 500 ||
        invalid_bootstrap_replicates * 100 > bootstrap_replicates) {
      throw std::runtime_error("too many invalid bootstrap comparisons");
    }

    std::filesystem::path output_path(argv[6]);
    if (output_path.has_parent_path()) {
      std::filesystem::create_directories(output_path.parent_path());
    }
    std::ofstream output(output_path);
    output << "feature_set,test_signal_entries,test_background_entries,"
              "signal_sumw,signal_sumw2,signal_neff,signal_max_weight_fraction,"
              "background_sumw,background_sumw2,background_neff,"
              "background_max_weight_fraction,bdt_signal_efficiency,"
              "bdt_photon_efficiency,bdt_RZ,box_signal_efficiency,"
              "box_photon_efficiency,box_RZ,RZ_ratio,log_RZ_ratio,"
              "coupling_advantage,bootstrap_replicates,bootstrap_valid,"
              "bootstrap_invalid,bootstrap_seed,"
              "RZ_ratio_q025,RZ_ratio_q16,RZ_ratio_q50,RZ_ratio_q84,"
              "RZ_ratio_q975,coupling_q025,coupling_q05,coupling_q16,"
              "coupling_q50,coupling_q84,coupling_q95,coupling_q975\n";
    output << std::setprecision(12) << feature_set << ',' << signal.size()
           << ',' << background.size() << ',' << signal_weights.sum << ','
           << signal_weights.sum_squared << ',' << signal_weights.effective_events
           << ',' << signal_weights.maximum_fraction << ','
           << background_weights.sum << ',' << background_weights.sum_squared
           << ',' << background_weights.effective_events << ','
           << background_weights.maximum_fraction << ','
           << nominal.bdt.signal_efficiency << ','
           << nominal.bdt.background_efficiency << ','
           << nominal.bdt.improvement << ','
           << nominal.box.signal_efficiency << ','
           << nominal.box.background_efficiency << ','
           << nominal.box.improvement << ',' << nominal.ratio << ','
           << nominal.log_ratio << ',' << nominal.coupling_advantage << ','
           << bootstrap_replicates << ',' << ratios.size() << ','
           << invalid_bootstrap_replicates << ',' << bootstrap_seed << ','
           << quantile(ratios, 0.025) << ',' << quantile(ratios, 0.16) << ','
           << quantile(ratios, 0.50) << ',' << quantile(ratios, 0.84) << ','
           << quantile(ratios, 0.975) << ','
           << quantile(coupling_advantages, 0.025) << ','
           << quantile(coupling_advantages, 0.05) << ','
           << quantile(coupling_advantages, 0.16) << ','
           << quantile(coupling_advantages, 0.50) << ','
           << quantile(coupling_advantages, 0.84) << ','
           << quantile(coupling_advantages, 0.95) << ','
           << quantile(coupling_advantages, 0.975) << '\n';

    const std::filesystem::path distribution_path =
        output_path.parent_path() /
        (output_path.stem().string() + "_bootstrap.csv");
    std::ofstream distribution(distribution_path);
    distribution << "replicate,RZ_ratio,log_RZ_ratio,coupling_advantage\n";
    for (std::size_t index = 0; index < ratios.size(); ++index) {
      distribution << index << ',' << std::setprecision(12) << ratios[index]
                   << ',' << log_ratios[index] << ','
                   << coupling_advantages[index] << '\n';
    }
    std::cout << std::setprecision(8) << feature_set
              << " RZ_BDT/RZ_box=" << nominal.ratio
              << " coupling_advantage=" << nominal.coupling_advantage
              << " bootstrap95=["
              << quantile(coupling_advantages, 0.025) << ','
              << quantile(coupling_advantages, 0.975) << "]\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
