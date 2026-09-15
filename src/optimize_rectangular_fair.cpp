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
#include <utility>
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

struct Candidate {
  Box box;
  Result training;
  Result validation;
};

bool passes(const Event& event, const Box& box, std::size_t feature_count) {
  for (std::size_t index = 0; index < feature_count; ++index) {
    if (event.value[index] < box.lower[index] ||
        event.value[index] > box.upper[index]) {
      return false;
    }
  }
  return true;
}

Result evaluate(const std::vector<Event>& signal,
                const std::vector<Event>& background,
                const Box& box, std::size_t feature_count,
                double photon_xs, double dis_xs) {
  double signal_total = 0.0;
  double signal_pass = 0.0;
  double background_total = 0.0;
  double background_pass = 0.0;
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
  if (baseline > 0.0 && remaining > 0.0) {
    result.improvement =
        result.signal_efficiency * std::sqrt(baseline / remaining);
  }
  return result;
}

std::vector<Event> read_events(const std::string& path, bool photon,
                               std::size_t feature_count) {
  TFile file(path.c_str(), "READ");
  if (file.IsZombie()) throw std::runtime_error("cannot open " + path);
  auto* tree = dynamic_cast<TTree*>(file.Get("events"));
  if (!tree) throw std::runtime_error("missing events tree in " + path);
  double foam_weight = 0.0;
  double miss = 1.0;
  double qe2 = 0.0;
  double qa2 = 0.0;
  double pt = 0.0;
  double eta = 0.0;
  double energy = 0.0;
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

std::vector<double> weighted_candidates(const std::vector<Event>& signal,
                                        const std::vector<Event>& background,
                                        std::size_t feature,
                                        std::size_t quantiles) {
  double signal_weight = 0.0;
  double background_weight = 0.0;
  for (const auto& event : signal) signal_weight += event.weight;
  for (const auto& event : background) background_weight += event.weight;
  if (!(signal_weight > 0.0 && background_weight > 0.0)) return {};

  std::vector<std::pair<double, double>> values;
  values.reserve(signal.size() + background.size());
  for (const auto& event : signal) {
    values.emplace_back(event.value[feature],
                        0.5 * event.weight / signal_weight);
  }
  for (const auto& event : background) {
    values.emplace_back(event.value[feature],
                        0.5 * event.weight / background_weight);
  }
  std::sort(values.begin(), values.end(), [](const auto& left,
                                              const auto& right) {
    return left.first < right.first;
  });

  std::vector<double> result;
  result.reserve(quantiles + 1);
  std::size_t position = 0;
  double cumulative = 0.0;
  for (std::size_t index = 0; index <= quantiles; ++index) {
    const double target = static_cast<double>(index) /
                          static_cast<double>(quantiles);
    while (position + 1 < values.size() &&
           cumulative + values[position].second < target) {
      cumulative += values[position].second;
      ++position;
    }
    result.push_back(values[position].first);
  }
  std::sort(result.begin(), result.end());
  result.erase(std::unique(result.begin(), result.end()), result.end());
  return result;
}

Box open_box() {
  const double infinity = std::numeric_limits<double>::infinity();
  Box box;
  box.lower.fill(-infinity);
  box.upper.fill(infinity);
  return box;
}

Box coordinate_optimize(
    const std::vector<Event>& signal,
    const std::vector<Event>& background,
    Box box, const std::vector<std::size_t>& order,
    const std::array<std::vector<double>, kMaximumFeatures>& grids,
    std::size_t feature_count, double photon_xs, double dis_xs) {
  Result best = evaluate(signal, background, box, feature_count,
                         photon_xs, dis_xs);
  const double infinity = std::numeric_limits<double>::infinity();
  for (int pass = 0; pass < 6; ++pass) {
    bool changed = false;
    for (std::size_t feature : order) {
      const double before = best.improvement;
      Box local_box = box;
      Result local_best = best;

      std::vector<double> lower_values = grids[feature];
      lower_values.push_back(-infinity);
      for (double threshold : lower_values) {
        if (threshold > box.upper[feature]) continue;
        Box trial = box;
        trial.lower[feature] = threshold;
        const Result result = evaluate(signal, background, trial,
                                       feature_count, photon_xs, dis_xs);
        if (result.improvement > local_best.improvement) {
          local_best = result;
          local_box = trial;
        }
      }
      box = local_box;
      best = local_best;

      std::vector<double> upper_values = grids[feature];
      upper_values.push_back(infinity);
      local_box = box;
      local_best = best;
      for (double threshold : upper_values) {
        if (threshold < box.lower[feature]) continue;
        Box trial = box;
        trial.upper[feature] = threshold;
        const Result result = evaluate(signal, background, trial,
                                       feature_count, photon_xs, dis_xs);
        if (result.improvement > local_best.improvement) {
          local_best = result;
          local_box = trial;
        }
      }
      box = local_box;
      best = local_best;
      if (best.improvement > before + 1.0e-12) changed = true;
    }
    if (!changed) break;
  }
  return box;
}

std::vector<std::size_t> rotated_order(std::size_t feature_count,
                                       std::size_t shift,
                                       bool reverse) {
  std::vector<std::size_t> order(feature_count);
  std::iota(order.begin(), order.end(), 0);
  std::rotate(order.begin(), order.begin() + shift % feature_count,
              order.end());
  if (reverse) std::reverse(order.begin(), order.end());
  return order;
}

std::vector<Candidate> make_candidates(
    const std::vector<Event>& signal_training,
    const std::vector<Event>& background_training,
    const std::vector<Event>& signal_validation,
    const std::vector<Event>& background_validation,
    std::size_t feature_count, double photon_xs, double dis_xs,
    std::size_t quantiles, std::size_t restarts, unsigned int seed) {
  std::array<std::vector<double>, kMaximumFeatures> grids;
  for (std::size_t feature = 0; feature < feature_count; ++feature) {
    grids[feature] = weighted_candidates(signal_training, background_training,
                                         feature, quantiles);
    if (grids[feature].empty()) {
      throw std::runtime_error("empty threshold grid");
    }
  }

  std::vector<std::pair<Box, std::vector<std::size_t>>> starts;
  for (std::size_t shift = 0; shift < feature_count; ++shift) {
    starts.emplace_back(open_box(), rotated_order(feature_count, shift, false));
    starts.emplace_back(open_box(), rotated_order(feature_count, shift, true));
  }

  std::mt19937 generator(seed);
  for (std::size_t restart = 0; restart < restarts; ++restart) {
    Box box = open_box();
    std::vector<std::size_t> features(feature_count);
    std::iota(features.begin(), features.end(), 0);
    std::shuffle(features.begin(), features.end(), generator);
    const std::size_t restricted = 1 + restart % std::min<std::size_t>(3, feature_count);
    for (std::size_t item = 0; item < restricted; ++item) {
      const std::size_t feature = features[item];
      const auto& grid = grids[feature];
      const std::size_t third = std::max<std::size_t>(1, grid.size() / 3);
      std::uniform_int_distribution<std::size_t> low_pick(0, third - 1);
      std::uniform_int_distribution<std::size_t> high_pick(
          grid.size() - third, grid.size() - 1);
      const int mode = static_cast<int>((restart + item) % 3);
      if (mode != 1) box.lower[feature] = grid[low_pick(generator)];
      if (mode != 0) box.upper[feature] = grid[high_pick(generator)];
    }
    starts.emplace_back(box, rotated_order(feature_count, restart, restart % 2));
  }

  std::vector<Candidate> candidates;
  candidates.reserve(starts.size());
  for (const auto& start : starts) {
    Candidate candidate;
    candidate.box = coordinate_optimize(
        signal_training, background_training, start.first, start.second,
        grids, feature_count, photon_xs, dis_xs);
    candidate.training = evaluate(signal_training, background_training,
                                  candidate.box, feature_count,
                                  photon_xs, dis_xs);
    candidate.validation = evaluate(signal_validation, background_validation,
                                    candidate.box, feature_count,
                                    photon_xs, dis_xs);
    candidates.push_back(candidate);
  }
  return candidates;
}

std::string printable(double value) {
  if (std::isinf(value)) return value < 0.0 ? "-inf" : "inf";
  std::ostringstream output;
  output << std::setprecision(12) << value;
  return output.str();
}

void write_bounds(std::ostream& output, const Box& box,
                  std::size_t feature_count) {
  for (std::size_t feature = 0; feature < kMaximumFeatures; ++feature) {
    if (feature >= feature_count) {
      output << ",NA,NA";
    } else {
      output << ',' << printable(box.lower[feature]) << ','
             << printable(box.upper[feature]);
    }
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 14 || argc > 17) {
      throw std::runtime_error(
          "usage: optimize_rectangular_fair signal_train.root "
          "background_train.root signal_validation.root "
          "background_validation.root signal_test.root background_test.root "
          "output.csv signal_type mass signal_xs photon_xs dis_xs "
          "electron|electron_qa2 [quantiles] [restarts] [optimizer_seed]");
    }
    const std::string feature_set = argv[13];
    if (feature_set != "electron" && feature_set != "electron_qa2") {
      throw std::runtime_error("feature set must be electron or electron_qa2");
    }
    const std::size_t feature_count = feature_set == "electron" ? 4 : 5;
    const double mass = std::stod(argv[9]);
    const double signal_xs = std::stod(argv[10]);
    const double photon_xs = std::stod(argv[11]);
    const double dis_xs = std::stod(argv[12]);
    const std::size_t quantiles = argc >= 15
        ? static_cast<std::size_t>(std::stoul(argv[14])) : 80;
    const std::size_t restarts = argc >= 16
        ? static_cast<std::size_t>(std::stoul(argv[15])) : 20;
    const unsigned int seed = argc >= 17
        ? static_cast<unsigned int>(std::stoul(argv[16])) : 8675309U;
    if (quantiles < 10 || restarts < 1) {
      throw std::runtime_error("quantiles must be >=10 and restarts >=1");
    }

    const auto signal_training = read_events(argv[1], false, feature_count);
    const auto background_training = read_events(argv[2], true, feature_count);
    const auto signal_validation = read_events(argv[3], false, feature_count);
    const auto background_validation = read_events(argv[4], true, feature_count);
    const auto signal_test = read_events(argv[5], false, feature_count);
    const auto background_test = read_events(argv[6], true, feature_count);

    const auto candidates = make_candidates(
        signal_training, background_training,
        signal_validation, background_validation,
        feature_count, photon_xs, dis_xs, quantiles, restarts, seed);
    const auto best = std::max_element(
        candidates.begin(), candidates.end(), [](const Candidate& left,
                                                  const Candidate& right) {
      if (left.validation.improvement != right.validation.improvement) {
        return left.validation.improvement < right.validation.improvement;
      }
      return left.training.improvement < right.training.improvement;
    });
    if (best == candidates.end()) throw std::runtime_error("no candidates");
    const Result test = evaluate(signal_test, background_test, best->box,
                                 feature_count, photon_xs, dis_xs);

    std::filesystem::path output_path(argv[7]);
    if (output_path.has_parent_path()) {
      std::filesystem::create_directories(output_path.parent_path());
    }
    const std::string bounds_header =
        "logQe2_min,logQe2_max,pt_min,pt_max,eta_min,eta_max,"
        "energy_min,energy_max,logQA2_min,logQA2_max";
    std::ofstream output(output_path);
    output << "signal_type,mass_GeV,feature_set,quantiles,restarts,"
              "optimizer_seed,candidate_count,train_signal_entries,"
              "train_background_entries,validation_signal_entries,"
              "validation_background_entries,test_signal_entries,"
              "test_background_entries,training_signal_efficiency,"
              "training_photon_efficiency,training_significance_improvement,"
              "validation_signal_efficiency,validation_photon_efficiency,"
              "validation_significance_improvement,signal_efficiency,"
              "photon_background_efficiency,significance_improvement,"
              "coupling_reach_improvement,signal_xs_pb,photon_xs_pb,dis_xs_pb,"
           << bounds_header << '\n';
    output << std::setprecision(12) << argv[8] << ',' << mass << ','
           << feature_set << ',' << quantiles << ',' << restarts << ','
           << seed << ',' << candidates.size() << ','
           << signal_training.size() << ',' << background_training.size() << ','
           << signal_validation.size() << ',' << background_validation.size() << ','
           << signal_test.size() << ',' << background_test.size() << ','
           << best->training.signal_efficiency << ','
           << best->training.background_efficiency << ','
           << best->training.improvement << ','
           << best->validation.signal_efficiency << ','
           << best->validation.background_efficiency << ','
           << best->validation.improvement << ','
           << test.signal_efficiency << ',' << test.background_efficiency << ','
           << test.improvement << ','
           << (test.improvement > 0.0
                   ? 1.0 - 1.0 / std::sqrt(test.improvement) : 0.0)
           << ',' << signal_xs << ',' << photon_xs << ',' << dis_xs;
    write_bounds(output, best->box, feature_count);
    output << '\n';

    const std::filesystem::path candidate_path =
        output_path.parent_path() /
        (output_path.stem().string() + "_candidates.csv");
    std::ofstream candidate_output(candidate_path);
    candidate_output << "candidate,training_significance_improvement,"
                        "validation_significance_improvement,"
                     << bounds_header << '\n';
    for (std::size_t index = 0; index < candidates.size(); ++index) {
      candidate_output << std::setprecision(12) << index << ','
                       << candidates[index].training.improvement << ','
                       << candidates[index].validation.improvement;
      write_bounds(candidate_output, candidates[index].box, feature_count);
      candidate_output << '\n';
    }

    std::cout << std::setprecision(8) << argv[8] << " m=" << mass << ' '
              << feature_set << " rectangular validation="
              << best->validation.improvement << " test="
              << test.improvement << " candidates=" << candidates.size()
              << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
