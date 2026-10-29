// Evaluation-only validation reselection. No training and no final-test inputs.
#define main original_export_refit_scores_unused_main
#include "../../src/export_refit_scores.cpp"
#undef main
namespace Threshold {
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


}
std::vector<Threshold::WeightedScore> validation_scores(const std::string& path,
    bool photon,Model& model,const std::string& output,double expected_mass) {
  TFile file(path.c_str(),"READ");
  if(file.IsZombie())throw std::runtime_error("Cannot open validation file: "+path);
  auto*tree=dynamic_cast<TTree*>(file.Get("events"));
  auto*norm=dynamic_cast<TParameter<double>*>(file.Get("pb_per_foam_weight"));
  if(!tree||tree->GetEntries()<1||!norm||!std::isfinite(norm->GetVal())||norm->GetVal()<=0)
    throw std::runtime_error("Invalid validation file: "+path);
  if(photon&&!close_number(norm->GetVal(),1.))throw std::runtime_error("Expected merged photon normalization 1");
  double fw=0,miss=1,qe2=0,t=0,pt=0,eta=0,energy=0,mass=0;tree->SetBranchStatus("*",0);
  bind(*tree,path,"foam_weight",&fw);bind(*tree,path,"Qe2",&qe2);bind(*tree,path,"QA2",&t);
  bind(*tree,path,"electron_pt",&pt);bind(*tree,path,"electron_eta",&eta);bind(*tree,path,"electron_energy",&energy);
  bind(*tree,path,photon?"cut_mass":"mass",&mass);
  if(photon)bind(*tree,path,"photon_miss_probability",&miss);
  std::ofstream csv(output);if(!csv)throw std::runtime_error("Cannot write validation scores: "+output);
  csv<<"score,event_weight_pb\n"<<std::setprecision(17);
  std::vector<Threshold::WeightedScore> result;result.reserve(tree->GetEntries());
  for(Long64_t i=0;i<tree->GetEntries();++i){
    if(tree->GetEntry(i)<=0)throw std::runtime_error("Cannot read validation event");
    if(!close_number(mass,expected_mass))throw std::runtime_error("Validation sample mass mismatch");
    if(!(qe2>0&&t>0&&fw>=0&&miss>0&&miss<=1))throw std::runtime_error("Invalid validation event");
    std::array<double,kFeatures> values{std::log10(qe2),pt,eta,energy,std::log10(t)};
    double score=model.score(values),weight=fw*norm->GetVal()*(photon?miss:1.);
    if(!std::isfinite(score)||!std::isfinite(weight))throw std::runtime_error("Nonfinite score or weight");
    result.push_back({score,weight});csv<<score<<","<<weight<<"\n";
  }
  if(!csv)throw std::runtime_error("Validation score write failed");return result;
}
int self_test(){
  using W=Threshold::WeightedScore;
  auto tied=Threshold::optimize(std::vector<W>{{.5,1},{.5,2}},std::vector<W>{{.5,3}},1,1);
  if(tied.threshold!=.5||std::abs(tied.improvement-1)>1e-14)return 10;
  std::vector<W> s{{.9,1},{.7,1}},b{{.8,1},{.1,1}};
  auto a=Threshold::optimize(s,b,1,1);auto m=Threshold::metrics_at_threshold(s,b,a.threshold,1,1);
  if(a.threshold!=.7||std::abs(a.improvement-std::sqrt(2./1.5))>1e-14||std::abs(a.improvement-m.improvement)>1e-14)return 11;
  auto none=Threshold::optimize(std::vector<W>{{.1,1}},std::vector<W>{{.9,1}},1,1);
  if(none.threshold!=.1||none.improvement!=1)return 12;
  std::cout<<"Exact original C++ threshold optimizer: ties, optimum, inclusive threshold, all-pass tests passed\n";return 0;
}
int main(int argc,char**argv){
 try{
  if(argc==2&&std::string(argv[1])=="--self-test")return self_test();
  if(argc!=10)throw std::runtime_error("Usage: rethreshold_validation signal_validation.root photon_validation.root weights.xml original_metrics.csv output_dir feature_set photon_xs dis_xs expected_profile");
  const std::string signal=argv[1],photon=argv[2],xml=argv[3],template_csv=argv[4],output=argv[5],feature=argv[6],expected_profile=argv[9];
  if(feature!="electron"&&feature!="electron_qa2")throw std::runtime_error("Invalid feature set");
  for(auto path:{signal,photon})if(std::filesystem::path(path).filename().string().find("test")!=std::string::npos)throw std::runtime_error("Final test inputs forbidden");
  auto original=read_selected_row(template_csv);if(original.at("model_profile")!=expected_profile||original.at("feature_set")!=feature)throw std::runtime_error("Candidate profile or features disagree");
  double px=parse_number(argv[7],"photon_xs"),dx=parse_number(argv[8],"dis_xs");
  if(!(px>0&&dx>=0))throw std::runtime_error("Invalid rates");
  std::filesystem::create_directories(output);Model model(xml,feature,expected_profile);
  double expected_mass=required_number(original,"mass_GeV");
  auto s=validation_scores(signal,false,model,output+"/validation_signal_scores.csv",expected_mass);
  auto b=validation_scores(photon,true,model,output+"/validation_photon_scores.csv",expected_mass);
  auto best=Threshold::optimize(s,b,px,dx);auto m=Threshold::metrics_at_threshold(s,b,best.threshold,px,dx);
  auto no_dis=Threshold::metrics_at_threshold(s,b,best.threshold,px,0.);
  double sx=required_number(original,"signal_xs_pb");
  std::ofstream csv(output+"/validation_metrics.csv");if(!csv)throw std::runtime_error("Cannot write metrics");
  csv<<"evaluation_signal_entries,evaluation_background_entries,validation_auc,validation_threshold,validation_signal_efficiency,validation_photon_efficiency,validation_significance_improvement,auc,signal_efficiency,photon_background_efficiency,significance_improvement,signal_efficiency_photon_only,photon_efficiency_photon_only,significance_improvement_photon_only,signal_efficiency_mc_error,photon_efficiency_mc_error,significance_improvement_mc_error,photon_xs_pb,dis_xs_pb,ml_signal_xs_pb,ml_photon_xs_pb,ml_total_background_xs_pb,coupling_reach_improvement\n"<<std::setprecision(12)
     <<s.size()<<","<<b.size()<<","<<best.auc<<","<<best.threshold<<","<<best.signal_efficiency<<","<<best.background_efficiency<<","<<best.improvement<<","<<m.auc<<","<<m.signal_efficiency<<","<<m.background_efficiency<<","<<m.improvement<<","<<no_dis.signal_efficiency<<","<<no_dis.background_efficiency<<","<<no_dis.improvement<<","<<m.signal_efficiency_error<<","<<m.background_efficiency_error<<","<<m.improvement_error<<","<<px<<","<<dx<<","<<sx*m.signal_efficiency<<","<<px*m.background_efficiency<<","<<px*m.background_efficiency+dx<<","<<(m.improvement>0?1-1/std::sqrt(m.improvement):0)<<"\n";
  std::cout<<"Validation only profile="<<expected_profile<<" threshold="<<best.threshold<<" RZ="<<best.improvement<<"\n";
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
