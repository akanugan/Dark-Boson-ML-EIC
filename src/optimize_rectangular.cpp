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
#include <stdexcept>
#include <string>
#include <sstream>
#include <vector>

namespace {

constexpr std::size_t kMaximumFeatures = 5;

struct Event {
  std::array<double, kMaximumFeatures> value{};
  double weight = 0.0;
};

struct Box {
  std::array<double, kMaximumFeatures> lower{};
  std::array<double, kMaximumFeatures> upper{};
};

struct Result {
  double signal_efficiency = 0.0;
  double background_efficiency = 0.0;
  double improvement = 0.0;
};

bool passes(const Event& event, const Box& box, std::size_t feature_count) {
  for (std::size_t index = 0; index < feature_count; ++index) {
    if (event.value[index] < box.lower[index] ||
        event.value[index] > box.upper[index]) return false;
  }
  return true;
}

Result evaluate(const std::vector<Event>& signal,
                const std::vector<Event>& background,
                const Box& box, std::size_t feature_count,
                double photon_xs, double dis_xs) {
  double signal_total = 0.0, signal_pass = 0.0;
  double background_total = 0.0, background_pass = 0.0;
  for (const auto& event : signal) {
    signal_total += event.weight;
    if (passes(event, box, feature_count)) signal_pass += event.weight;
  }
  for (const auto& event : background) {
    background_total += event.weight;
    if (passes(event, box, feature_count)) background_pass += event.weight;
  }
  Result result;
  if (!(signal_total > 0.0 && background_total > 0.0)) return result;
  result.signal_efficiency = signal_pass / signal_total;
  result.background_efficiency = background_pass / background_total;
  const double baseline = photon_xs + dis_xs;
  const double remaining = photon_xs * result.background_efficiency + dis_xs;
  if (remaining > 0.0) {
    result.improvement = result.signal_efficiency * std::sqrt(baseline / remaining);
  }
  return result;
}

std::vector<Event> read_events(const std::string& path, bool photon,
                               std::size_t feature_count) {
  TFile file(path.c_str(), "READ");
  if (file.IsZombie()) throw std::runtime_error("cannot open " + path);
  auto* tree = dynamic_cast<TTree*>(file.Get("events"));
  if (!tree) throw std::runtime_error("missing events tree in " + path);
  double foam_weight = 0.0, miss = 1.0;
  double qe2 = 0.0, qa2 = 0.0, pt = 0.0, eta = 0.0, energy = 0.0;
  tree->SetBranchAddress("foam_weight", &foam_weight);
  tree->SetBranchAddress("Qe2", &qe2);
  tree->SetBranchAddress("QA2", &qa2);
  tree->SetBranchAddress("electron_pt", &pt);
  tree->SetBranchAddress("electron_eta", &eta);
  tree->SetBranchAddress("electron_energy", &energy);
  if (photon) tree->SetBranchAddress("photon_miss_probability", &miss);
  double pb_per_weight = 1.0;
  if (auto* parameter = dynamic_cast<TParameter<double>*>(
          file.Get("pb_per_foam_weight"))) {
    pb_per_weight = parameter->GetVal();
  }
  std::vector<Event> events;
  events.reserve(static_cast<std::size_t>(tree->GetEntries()));
  for (Long64_t index = 0; index < tree->GetEntries(); ++index) {
    tree->GetEntry(index);
    Event event;
    event.value[0] = std::log10(std::max(qe2, 1.0e-30));
    event.value[1] = pt;
    event.value[2] = eta;
    event.value[3] = energy;
    if (feature_count == 5) {
      event.value[4] = std::log10(std::max(qa2, 1.0e-30));
    }
    event.weight = foam_weight * pb_per_weight * (photon ? miss : 1.0);
    events.push_back(event);
  }
  return events;
}

void split(const std::vector<Event>& input, std::vector<Event>& validation,
           std::vector<Event>& test) {
  for (std::size_t index = 0; index < input.size(); ++index) {
    (index % 2 == 0 ? validation : test).push_back(input[index]);
  }
}

std::vector<double> candidates(const std::vector<Event>& signal,
                               const std::vector<Event>& background,
                               std::size_t feature) {
  std::vector<double> values;
  values.reserve(signal.size() + background.size());
  for (const auto& event : signal) values.push_back(event.value[feature]);
  for (const auto& event : background) values.push_back(event.value[feature]);
  std::sort(values.begin(), values.end());
  std::vector<double> result;
  if (values.empty()) return result;
  constexpr std::size_t kQuantiles = 80;
  for (std::size_t index = 0; index <= kQuantiles; ++index) {
    const std::size_t position =
        index * (values.size() - 1) / kQuantiles;
    result.push_back(values[position]);
  }
  result.erase(std::unique(result.begin(), result.end()), result.end());
  return result;
}

Box optimize(const std::vector<Event>& signal,
             const std::vector<Event>& background,
             std::size_t feature_count, double photon_xs, double dis_xs) {
  const double infinity = std::numeric_limits<double>::infinity();
  Box box;
  box.lower.fill(-infinity);
  box.upper.fill(infinity);
  Result best = evaluate(signal, background, box, feature_count,
                         photon_xs, dis_xs);
  std::array<std::vector<double>, kMaximumFeatures> grids;
  for (std::size_t feature = 0; feature < feature_count; ++feature) {
    grids[feature] = candidates(signal, background, feature);
  }
  for (int pass = 0; pass < 6; ++pass) {
    bool changed = false;
    for (std::size_t feature = 0; feature < feature_count; ++feature) {
      const double improvement_before_feature = best.improvement;
      Box local_best_box = box;
      Result local_best = best;
      std::vector<double> lower_candidates = grids[feature];
      lower_candidates.push_back(-infinity);
      for (double threshold : lower_candidates) {
        if (threshold > box.upper[feature]) continue;
        Box trial = box;
        trial.lower[feature] = threshold;
        const Result result = evaluate(signal, background, trial, feature_count,
                                       photon_xs, dis_xs);
        if (result.improvement > local_best.improvement) {
          local_best = result;
          local_best_box = trial;
        }
      }
      box = local_best_box;
      best = local_best;

      std::vector<double> upper_candidates = grids[feature];
      upper_candidates.push_back(infinity);
      local_best_box = box;
      local_best = best;
      for (double threshold : upper_candidates) {
        if (threshold < box.lower[feature]) continue;
        Box trial = box;
        trial.upper[feature] = threshold;
        const Result result = evaluate(signal, background, trial, feature_count,
                                       photon_xs, dis_xs);
        if (result.improvement > local_best.improvement) {
          local_best = result;
          local_best_box = trial;
        }
      }
      box = local_best_box;
      best = local_best;
      changed = changed || best.improvement > improvement_before_feature + 1.0e-12;
    }
    if (!changed) break;
  }
  return box;
}

std::string printable(double value) {
  if (std::isinf(value)) return value < 0.0 ? "-inf" : "inf";
  std::ostringstream output;
  output << std::setprecision(12) << value;
  return output.str();
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 10) {
      throw std::runtime_error(
          "usage: optimize_rectangular signal_test.root background_test.root "
          "output.csv signal_type mass signal_xs photon_xs dis_xs "
          "electron|electron_qa2");
    }
    const std::string feature_set = argv[9];
    if (feature_set != "electron" && feature_set != "electron_qa2") {
      throw std::runtime_error("feature set must be electron or electron_qa2");
    }
    const std::size_t feature_count = feature_set == "electron" ? 4 : 5;
    const double mass = std::stod(argv[5]);
    const double signal_xs = std::stod(argv[6]);
    const double photon_xs = std::stod(argv[7]);
    const double dis_xs = std::stod(argv[8]);
    const auto signal_all = read_events(argv[1], false, feature_count);
    const auto background_all = read_events(argv[2], true, feature_count);
    std::vector<Event> signal_validation, signal_test;
    std::vector<Event> background_validation, background_test;
    split(signal_all, signal_validation, signal_test);
    split(background_all, background_validation, background_test);
    const Box box = optimize(signal_validation, background_validation,
                             feature_count, photon_xs, dis_xs);
    const Result result = evaluate(signal_test, background_test, box,
                                   feature_count, photon_xs, dis_xs);
    std::filesystem::path output_path(argv[3]);
    if (output_path.has_parent_path()) {
      std::filesystem::create_directories(output_path.parent_path());
    }
    std::ofstream output(output_path);
    output << "signal_type,mass_GeV,feature_set,validation_signal_entries,"
              "validation_background_entries,test_signal_entries,"
              "test_background_entries,signal_efficiency,"
              "photon_background_efficiency,significance_improvement,"
              "coupling_reach_improvement,signal_xs_pb,photon_xs_pb,dis_xs_pb,"
              "logQe2_min,logQe2_max,pt_min,pt_max,eta_min,eta_max,"
              "energy_min,energy_max,logQA2_min,logQA2_max\n";
    output << std::setprecision(12) << argv[4] << ',' << mass << ','
           << feature_set << ',' << signal_validation.size() << ','
           << background_validation.size() << ',' << signal_test.size() << ','
           << background_test.size() << ',' << result.signal_efficiency << ','
           << result.background_efficiency << ',' << result.improvement << ','
           << (result.improvement > 0.0
                   ? 1.0 - 1.0 / std::sqrt(result.improvement)
                   : 0.0)
           << ',' << signal_xs << ',' << photon_xs << ',' << dis_xs;
    for (std::size_t feature = 0; feature < kMaximumFeatures; ++feature) {
      if (feature >= feature_count) {
        output << ",NA,NA";
      } else {
        output << ',' << printable(box.lower[feature]) << ','
               << printable(box.upper[feature]);
      }
    }
    output << '\n';
    std::cout << std::setprecision(8) << argv[4] << " m=" << mass << ' '
              << feature_set << " rectangular improvement="
              << result.improvement << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
