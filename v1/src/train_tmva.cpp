#include <TMVA/Config.h>
#include <TMVA/DataLoader.h>
#include <TMVA/Factory.h>
#include <TMVA/Reader.h>
#include <TMVA/Tools.h>

#include <TFile.h>
#include <TParameter.h>
#include <TRandom.h>
#include <TTree.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct WeightedScore {
  double score = 0.0;
  double weight = 0.0;
};

struct Metrics {
  double auc = 0.0;
  double threshold = 0.0;
  double signal_efficiency = 0.0;
  double background_efficiency = 0.0;
  double improvement = 0.0;
  double signal_efficiency_no_dis = 0.0;
  double background_efficiency_no_dis = 0.0;
  double improvement_no_dis = 0.0;
  double signal_efficiency_error = 0.0;
  double background_efficiency_error = 0.0;
  double improvement_error = 0.0;
};

struct Arguments {
  std::string signal_train;
  std::string signal_test;
  std::string background_train;
  std::string background_test;
  std::string output_dir;
  std::string signal_type;
  double mass = 0.0;
  double signal_xs = 0.0;
  double photon_xs = 0.0;
  double dis_xs = 0.0;
  std::string feature_set = "electron";
  std::string model_profile = "depth3";
  unsigned int random_seed = 12345U;
  std::string evaluation_mode = "split";
};

Arguments parse_arguments(int argc, char** argv) {
  if (argc < 11 || argc > 15) {
    throw std::runtime_error(
        "usage: train_tmva signal_train.root signal_test.root "
        "background_train.root background_test.root output_dir signal_type "
        "mass signal_xs photon_xs dis_xs [electron|electron_qa2] "
        "[depth2|depth3|depth4|depth3_800] [random_seed] "
        "[split|validation_all]");
  }
  Arguments args;
  args.signal_train = argv[1];
  args.signal_test = argv[2];
  args.background_train = argv[3];
  args.background_test = argv[4];
  args.output_dir = argv[5];
  args.signal_type = argv[6];
  args.mass = std::stod(argv[7]);
  args.signal_xs = std::stod(argv[8]);
  args.photon_xs = std::stod(argv[9]);
  args.dis_xs = std::stod(argv[10]);
  if (argc >= 12) args.feature_set = argv[11];
  if (argc >= 13) args.model_profile = argv[12];
  if (argc >= 14) args.random_seed =
      static_cast<unsigned int>(std::stoul(argv[13]));
  if (argc >= 15) args.evaluation_mode = argv[14];
  if (args.feature_set != "electron" && args.feature_set != "electron_qa2") {
    throw std::runtime_error("feature set must be electron or electron_qa2");
  }
  if (args.model_profile != "depth2" &&
      args.model_profile != "depth3" &&
      args.model_profile != "depth4" &&
      args.model_profile != "depth3_800") {
    throw std::runtime_error(
        "model profile must be depth2, depth3, depth4, or depth3_800");
  }
  if (args.evaluation_mode != "split" &&
      args.evaluation_mode != "validation_all") {
    throw std::runtime_error(
        "evaluation mode must be split or validation_all");
  }
  return args;
}

std::string bdt_options(const std::string& profile) {
  int trees = 400;
  int depth = 3;
  if (profile == "depth2") depth = 2;
  if (profile == "depth4") depth = 4;
  if (profile == "depth3_800") trees = 800;
  std::ostringstream options;
  options << "!H:!V:NTrees=" << trees
          << ":MinNodeSize=2.5%:MaxDepth=" << depth
          << ":BoostType=Grad:Shrinkage=0.05:UseBaggedBoost:"
             "BaggedSampleFraction=0.6:nCuts=30:"
             "NegWeightTreatment=IgnoreNegWeightsInTraining";
  return options.str();
}

TTree* get_tree(TFile& file) {
  auto* tree = dynamic_cast<TTree*>(file.Get("events"));
  if (!tree) throw std::runtime_error("missing events tree");
  return tree;
}

double weighted_auc(std::vector<WeightedScore> signal,
                    std::vector<WeightedScore> background) {
  std::sort(background.begin(), background.end(),
            [](const auto& a, const auto& b) { return a.score < b.score; });
  std::vector<double> prefix(background.size() + 1, 0.0);
  for (size_t i = 0; i < background.size(); ++i) {
    prefix[i + 1] = prefix[i] + background[i].weight;
  }
  const double total_signal = [&]() {
    double sum = 0.0;
    for (const auto& event : signal) sum += event.weight;
    return sum;
  }();
  const double total_background = prefix.back();
  if (!(total_signal > 0.0 && total_background > 0.0)) return 0.0;

  double concordant = 0.0;
  for (const auto& event : signal) {
    const auto lower = std::lower_bound(
        background.begin(), background.end(), event.score,
        [](const WeightedScore& a, double score) { return a.score < score; });
    const auto upper = std::upper_bound(
        background.begin(), background.end(), event.score,
        [](double score, const WeightedScore& a) { return score < a.score; });
    const size_t low_index = static_cast<size_t>(lower - background.begin());
    const size_t high_index = static_cast<size_t>(upper - background.begin());
    const double lower_weight = prefix[low_index];
    const double equal_weight = prefix[high_index] - prefix[low_index];
    concordant += event.weight * (lower_weight + 0.5 * equal_weight);
  }
  return concordant / (total_signal * total_background);
}

double efficiency_error(const std::vector<WeightedScore>& events,
                        double efficiency) {
  double sum_weight = 0.0, sum_weight_squared = 0.0;
  for (const auto& event : events) {
    sum_weight += event.weight;
    sum_weight_squared += event.weight * event.weight;
  }
  if (!(sum_weight_squared > 0.0)) return 0.0;
  const double effective_events =
      sum_weight * sum_weight / sum_weight_squared;
  return std::sqrt(std::max(0.0, efficiency * (1.0 - efficiency) /
                                     effective_events));
}

Metrics metrics_at_threshold(const std::vector<WeightedScore>& signal,
                             const std::vector<WeightedScore>& background,
                             double threshold, double photon_xs,
                             double dis_xs) {
  Metrics result;
  result.threshold = threshold;
  result.auc = weighted_auc(signal, background);
  double signal_total = 0.0, signal_pass = 0.0;
  double background_total = 0.0, background_pass = 0.0;
  for (const auto& event : signal) {
    signal_total += event.weight;
    if (event.score >= threshold) signal_pass += event.weight;
  }
  for (const auto& event : background) {
    background_total += event.weight;
    if (event.score >= threshold) background_pass += event.weight;
  }
  if (!(signal_total > 0.0 && background_total > 0.0)) return result;
  result.signal_efficiency = signal_pass / signal_total;
  result.background_efficiency = background_pass / background_total;
  const double baseline_background = photon_xs + dis_xs;
  const double remaining_background =
      photon_xs * result.background_efficiency + dis_xs;
  result.improvement = result.signal_efficiency *
      std::sqrt(baseline_background / remaining_background);
  result.signal_efficiency_error =
      efficiency_error(signal, result.signal_efficiency);
  result.background_efficiency_error =
      efficiency_error(background, result.background_efficiency);
  const double first = result.signal_efficiency > 0.0
      ? result.signal_efficiency_error / result.signal_efficiency : 0.0;
  const double second = remaining_background > 0.0
      ? 0.5 * photon_xs * result.background_efficiency_error /
          remaining_background : 0.0;
  result.improvement_error =
      result.improvement * std::sqrt(first * first + second * second);
  return result;
}

Metrics optimize(const std::vector<WeightedScore>& signal,
                 const std::vector<WeightedScore>& background,
                 double photon_xs, double dis_xs) {
  Metrics best;
  best.auc = weighted_auc(signal, background);
  double total_signal = 0.0, total_background = 0.0;
  for (const auto& event : signal) {
    total_signal += event.weight;
  }
  for (const auto& event : background) {
    total_background += event.weight;
  }
  const double baseline_background = photon_xs + dis_xs;
  if (!(total_signal > 0.0 && total_background > 0.0 &&
        baseline_background > 0.0)) {
    return best;
  }

  struct LabeledScore {
    double score = 0.0;
    double weight = 0.0;
    bool signal = false;
  };
  std::vector<LabeledScore> scores;
  scores.reserve(signal.size() + background.size());
  for (const auto& event : signal) {
    scores.push_back({event.score, event.weight, true});
  }
  for (const auto& event : background) {
    scores.push_back({event.score, event.weight, false});
  }
  std::sort(scores.begin(), scores.end(), [](const auto& left,
                                              const auto& right) {
    return left.score > right.score;
  });

  double signal_pass = 0.0, background_pass = 0.0;
  for (std::size_t begin = 0; begin < scores.size();) {
    std::size_t end = begin;
    while (end < scores.size() && scores[end].score == scores[begin].score) {
      if (scores[end].signal) signal_pass += scores[end].weight;
      else background_pass += scores[end].weight;
      ++end;
    }
    const double signal_efficiency = signal_pass / total_signal;
    const double background_efficiency = background_pass / total_background;
    const double remaining_background =
        photon_xs * background_efficiency + dis_xs;
    const double improvement = signal_efficiency *
        std::sqrt(baseline_background / remaining_background);
    if (improvement > best.improvement) {
      best.threshold = scores[begin].score;
      best.signal_efficiency = signal_efficiency;
      best.background_efficiency = background_efficiency;
      best.improvement = improvement;
    }
    const double improvement_no_dis = background_efficiency > 0.0
        ? signal_efficiency / std::sqrt(background_efficiency) : 0.0;
    if (improvement_no_dis > best.improvement_no_dis) {
      best.signal_efficiency_no_dis = signal_efficiency;
      best.background_efficiency_no_dis = background_efficiency;
      best.improvement_no_dis = improvement_no_dis;
    }
    begin = end;
  }
  return best;
}

void split_validation_test(const std::vector<WeightedScore>& input,
                           std::vector<WeightedScore>& validation,
                           std::vector<WeightedScore>& test) {
  validation.clear();
  test.clear();
  for (size_t index = 0; index < input.size(); ++index) {
    if (index % 2 == 0) validation.push_back(input[index]);
    else test.push_back(input[index]);
  }
}

std::vector<WeightedScore> evaluate(TTree* tree,
                                    const std::string& weights_file,
                                    bool photon_background,
                                    const std::string& feature_set) {
  double foam_weight = 0.0, pb_per_weight = 1.0;
  double electron_pt = 0.0, electron_eta = 0.0, electron_energy = 0.0;
  double qe2 = 0.0, qa2 = 0.0;
  double photon_miss_probability = 1.0;
  tree->SetBranchAddress("foam_weight", &foam_weight);
  tree->SetBranchAddress("electron_pt", &electron_pt);
  tree->SetBranchAddress("electron_eta", &electron_eta);
  tree->SetBranchAddress("electron_energy", &electron_energy);
  tree->SetBranchAddress("Qe2", &qe2);
  tree->SetBranchAddress("QA2", &qa2);
  if (photon_background) {
    tree->SetBranchAddress("photon_miss_probability", &photon_miss_probability);
  }
  auto* file = tree->GetCurrentFile();
  if (file) {
    if (auto* parameter = dynamic_cast<TParameter<double>*>(
            file->Get("pb_per_foam_weight"))) {
      pb_per_weight = parameter->GetVal();
    }
  }

  float log_qe2 = 0.0F, log_qa2 = 0.0F, pt = 0.0F, eta = 0.0F, energy = 0.0F;
  TMVA::Reader reader("!Color:!Silent");
  reader.AddVariable("log10(Qe2)", &log_qe2);
  if (feature_set == "electron_qa2") {
    reader.AddVariable("log10(QA2)", &log_qa2);
  }
  reader.AddVariable("electron_pt", &pt);
  reader.AddVariable("electron_eta", &eta);
  reader.AddVariable("electron_energy", &energy);
  reader.BookMVA("BDTG", weights_file.c_str());

  std::vector<WeightedScore> result;
  result.reserve(static_cast<size_t>(tree->GetEntries()));
  for (Long64_t i = 0; i < tree->GetEntries(); ++i) {
    tree->GetEntry(i);
    log_qe2 = static_cast<float>(std::log10(std::max(qe2, 1.0e-30)));
    log_qa2 = static_cast<float>(std::log10(std::max(qa2, 1.0e-30)));
    pt = static_cast<float>(electron_pt);
    eta = static_cast<float>(electron_eta);
    energy = static_cast<float>(electron_energy);
    const double score = reader.EvaluateMVA("BDTG");
    const double miss = photon_background ? photon_miss_probability : 1.0;
    result.push_back({score, foam_weight * pb_per_weight * miss});
  }
  return result;
}

void write_scores(const std::filesystem::path& path,
                  const std::vector<WeightedScore>& signal,
                  const std::vector<WeightedScore>& background) {
  std::ofstream output(path);
  output << "class,score,event_weight_pb\n" << std::setprecision(12);
  for (const auto& event : signal) {
    output << "signal," << event.score << ',' << event.weight << '\n';
  }
  for (const auto& event : background) {
    output << "photon_background," << event.score << ',' << event.weight
           << '\n';
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Arguments args = parse_arguments(argc, argv);
    const std::filesystem::path output_dir =
        std::filesystem::absolute(args.output_dir);
    std::filesystem::create_directories(output_dir / "dataset");

    TFile signal_train_file(args.signal_train.c_str(), "READ");
    TFile signal_test_file(args.signal_test.c_str(), "READ");
    TFile background_train_file(args.background_train.c_str(), "READ");
    TFile background_test_file(args.background_test.c_str(), "READ");
    TTree* signal_train = get_tree(signal_train_file);
    TTree* signal_test = get_tree(signal_test_file);
    TTree* background_train = get_tree(background_train_file);
    TTree* background_test = get_tree(background_test_file);

    const auto original_directory = std::filesystem::current_path();
    std::filesystem::current_path(output_dir);
    const std::string training_output = "training.root";
    TFile tmva_output(training_output.c_str(), "RECREATE");
    TMVA::Tools::Instance();
    TMVA::Factory factory(
        "TMVAClassification", &tmva_output,
        "!V:!Silent:Color:DrawProgressBar:AnalysisType=Classification");
    gRandom->SetSeed(args.random_seed);
    TMVA::DataLoader loader("dataset");
    loader.AddVariable("log10(Qe2)", "log10_Qe2", "", 'F');
    if (args.feature_set == "electron_qa2") {
      loader.AddVariable("log10(QA2)", "log10_QA2", "", 'F');
    }
    loader.AddVariable("electron_pt", "electron_pt", "GeV", 'F');
    loader.AddVariable("electron_eta", "electron_eta", "", 'F');
    loader.AddVariable("electron_energy", "electron_energy", "GeV", 'F');
    loader.AddSignalTree(signal_train, 1.0, TMVA::Types::kTraining);
    loader.AddSignalTree(signal_test, 1.0, TMVA::Types::kTesting);
    loader.AddBackgroundTree(background_train, 1.0, TMVA::Types::kTraining);
    loader.AddBackgroundTree(background_test, 1.0, TMVA::Types::kTesting);
    loader.SetSignalWeightExpression("foam_weight");
    loader.SetBackgroundWeightExpression(
        "foam_weight*photon_miss_probability");
    loader.PrepareTrainingAndTestTree(
        "", "NormMode=EqualNumEvents:!V");
    const std::string options = bdt_options(args.model_profile);
    factory.BookMethod(&loader, TMVA::Types::kBDT, "BDTG", options.c_str());
    factory.TrainAllMethods();
    factory.TestAllMethods();
    factory.EvaluateAllMethods();
    tmva_output.Close();
    std::filesystem::current_path(original_directory);

    const std::string weights_file =
        (output_dir / "dataset" / "weights" /
         "TMVAClassification_BDTG.weights.xml").string();
    std::vector<WeightedScore> signal_scores =
        evaluate(signal_test, weights_file, false, args.feature_set);
    std::vector<WeightedScore> background_scores =
        evaluate(background_test, weights_file, true, args.feature_set);

    std::vector<WeightedScore> signal_validation, signal_final_test;
    std::vector<WeightedScore> background_validation, background_final_test;
    if (args.evaluation_mode == "validation_all") {
      signal_validation = signal_scores;
      background_validation = background_scores;
      signal_final_test = signal_scores;
      background_final_test = background_scores;
    } else {
      split_validation_test(signal_scores, signal_validation,
                            signal_final_test);
      split_validation_test(background_scores, background_validation,
                            background_final_test);
    }
    const Metrics validation_metrics =
        optimize(signal_validation, background_validation,
                 args.photon_xs, args.dis_xs);
    Metrics metrics = metrics_at_threshold(
        signal_final_test, background_final_test, validation_metrics.threshold,
        args.photon_xs, args.dis_xs);
    const Metrics photon_only_test = metrics_at_threshold(
        signal_final_test, background_final_test,
        validation_metrics.threshold, args.photon_xs, 0.0);
    metrics.signal_efficiency_no_dis = photon_only_test.signal_efficiency;
    metrics.background_efficiency_no_dis =
        photon_only_test.background_efficiency;
    metrics.improvement_no_dis = photon_only_test.improvement;
    write_scores(output_dir / "test_scores.csv", signal_scores,
                 background_scores);

    std::ofstream output(output_dir / "metrics.csv");
    output << "signal_type,mass_GeV,feature_set,model_profile,random_seed,"
              "evaluation_mode,"
              "train_signal_entries,"
              "train_background_entries,evaluation_signal_entries,"
              "evaluation_background_entries,validation_auc,validation_threshold,"
              "validation_signal_efficiency,validation_photon_efficiency,"
              "validation_significance_improvement,auc,signal_efficiency,"
              "photon_background_efficiency,significance_improvement,"
              "signal_efficiency_photon_only,photon_efficiency_photon_only,"
              "significance_improvement_photon_only,"
              "signal_efficiency_mc_error,photon_efficiency_mc_error,"
              "significance_improvement_mc_error,"
              "signal_xs_pb,photon_xs_pb,dis_xs_pb,"
              "ml_signal_xs_pb,ml_photon_xs_pb,ml_total_background_xs_pb,"
              "coupling_reach_improvement\n";
    output << std::setprecision(12) << args.signal_type << ',' << args.mass
           << ',' << args.feature_set << ',' << args.model_profile << ','
           << args.random_seed << ',' << args.evaluation_mode << ','
           << signal_train->GetEntries()
           << ',' << background_train->GetEntries() << ','
           << signal_test->GetEntries() << ',' << background_test->GetEntries()
           << ',' << validation_metrics.auc << ','
           << validation_metrics.threshold << ','
           << validation_metrics.signal_efficiency << ','
           << validation_metrics.background_efficiency << ','
           << validation_metrics.improvement << ',' << metrics.auc << ','
           << metrics.signal_efficiency << ',' << metrics.background_efficiency
           << ',' << metrics.improvement << ','
           << metrics.signal_efficiency_no_dis << ','
           << metrics.background_efficiency_no_dis << ','
           << metrics.improvement_no_dis << ','
           << metrics.signal_efficiency_error << ','
           << metrics.background_efficiency_error << ','
           << metrics.improvement_error << ',' << args.signal_xs << ','
           << args.photon_xs << ',' << args.dis_xs << ','
           << args.signal_xs * metrics.signal_efficiency << ','
           << args.photon_xs * metrics.background_efficiency << ','
           << args.photon_xs * metrics.background_efficiency + args.dis_xs
           << ',' << (metrics.improvement > 0.0
                          ? 1.0 - 1.0 / std::sqrt(metrics.improvement)
                          : 0.0) << '\n';
    std::cout << std::setprecision(8) << args.signal_type << " m=" << args.mass
              << " features=" << args.feature_set
              << " profile=" << args.model_profile
              << " AUC=" << metrics.auc
              << " improvement=" << metrics.improvement << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
