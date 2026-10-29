// Read-only ROOT photon integration diagnostics.
// Build: c++ -O2 -std=c++17 diagnostics.cpp $(root-config --cflags --libs) -o diagnostics
// Usage: ./diagnostics input.root [more.root ...] > diagnostics.jsonl
// One JSON object per input. Reads no events until ROOT files are complete.
#include <TFile.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TTree.h>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
std::string quote(const std::string& x) {
  std::string s="\"";
  for(char c:x) {
    if(c=='\\'||c=='\"') {s+='\\';s+=c;}
    else if(c=='\n') s+="\\n";
    else if(c=='\r') s+="\\r";
    else if(c=='\t') s+="\\t";
    else s+=c;
  }
  return s+'\"';
}
double parameter(TFile& f,const char* n) {
  auto* p=dynamic_cast<TParameter<double>*>(f.Get(n));
  if(!p) throw std::runtime_error(std::string("Missing parameter: ")+n);
  return p->GetVal();
}
std::map<std::string,std::string> config(const std::string& s) {
  std::map<std::string,std::string> out;
  std::istringstream in(s); std::string part;
  while(std::getline(in,part,';')) {
    auto p=part.find('='); if(p!=std::string::npos) out[part.substr(0,p)]=part.substr(p+1);
  }
  return out;
}
struct Distribution {
  std::vector<std::pair<double,double>> values;
  double sum=0,weighted=0;
  void add(double x,double w) {values.emplace_back(x,w);sum+=w;weighted+=w*x;}
  double quantile(double q) {
    if(sum<=0) return 0;
    std::sort(values.begin(),values.end());double acc=0;
    for(auto p:values) {acc+=p.second;if(acc>=q*sum)return p.first;}
    return values.back().first;
  }
  void write() {
    std::cout<<"{\"mean\":"<<(sum>0?weighted/sum:0)
      <<",\"p01\":"<<quantile(.01)<<",\"p10\":"<<quantile(.1)
      <<",\"p50\":"<<quantile(.5)<<",\"p90\":"<<quantile(.9)
      <<",\"p99\":"<<quantile(.99)<<"}";
  }
};
struct Group {
  long long n=0; double raw=0,sum=0,sum2=0,max=0,py_pos=0,py_neg=0;
  double py_pos2=0,py_neg2=0;
  Distribution energy,eta,t,photon_energy;
  std::vector<double> energy_edges{0,.01,.1,.5,1,2,5,10,1e12};
  std::vector<double> energy_bins=std::vector<double>(8,0.);
  void add(double raw_pb,double w,double py,double e,double et,double tr,double ge) {
    ++n;raw+=raw_pb;sum+=w;sum2+=w*w;max=std::max(max,w);
    if(py>0){py_pos+=w;py_pos2+=w*w;}
    if(py<0){py_neg+=w;py_neg2+=w*w;}
    energy.add(e,w);eta.add(et,w);t.add(tr,w);photon_energy.add(ge,w);
    for(size_t j=0;j<energy_bins.size();++j)if(e>=energy_edges[j]&&e<energy_edges[j+1]){energy_bins[j]+=w;break;}
  }
  void write(double attempts) {
    double err=std::sqrt(std::max(0.,sum2-(attempts>0?sum*sum/attempts:0.)));
    std::cout<<"{\"entries\":"<<n<<",\"raw_cross_section_pb\":"<<raw
      <<",\"effective_cross_section_pb\":"<<sum
      <<",\"effective_sum_weight_squared_pb2\":"<<sum2
      <<",\"event_sampling_error_pb\":"<<err
      <<",\"effective_n\":"<<(sum2>0?sum*sum/sum2:0)
      <<",\"max_effective_weight_pb\":"<<max
      <<",\"max_effective_weight_fraction\":"<<(sum>0?max/sum:0)
      <<",\"photon_py_positive_pb\":"<<py_pos<<",\"photon_py_negative_pb\":"<<py_neg
      <<",\"photon_py_positive_fraction\":"<<(sum>0?py_pos/sum:0)
      <<",\"photon_py_asymmetry\":"<<(sum>0?(py_pos-py_neg)/sum:0)
      <<",\"photon_py_asymmetry_naive_z\":"<<((py_pos2+py_neg2)>0?(py_pos-py_neg)/std::sqrt(py_pos2+py_neg2):0)
      <<",\"electron_energy_GeV\":";energy.write();
    std::cout<<",\"electron_eta\":";eta.write();
    std::cout<<",\"t_GeV2\":";t.write();
    std::cout<<",\"photon_energy_GeV\":";photon_energy.write();
    std::cout<<",\"electron_energy_bin_edges_GeV\":[";
    for(size_t j=0;j<energy_edges.size();++j){if(j)std::cout<<",";std::cout<<energy_edges[j];}
    std::cout<<"],\"electron_energy_effective_pb\":[";
    for(size_t j=0;j<energy_bins.size();++j){if(j)std::cout<<",";std::cout<<energy_bins[j];}
    std::cout<<"]}";
  }
};
void diagnose(const char* path) {
  TFile f(path,"READ");if(f.IsZombie())throw std::runtime_error("Cannot open ROOT file");
  auto* metadata=dynamic_cast<TNamed*>(f.Get("generator_configuration"));
  if(!metadata)throw std::runtime_error("Missing generator_configuration");
  std::string description=metadata->GetTitle();auto cfg=config(description);
  bool already_effective=(cfg["photon_region"]=="effective");
  double attempts=cfg.count("events")?std::stod(cfg["events"]):0.;
  auto* tree=dynamic_cast<TTree*>(f.Get("events"));if(!tree)throw std::runtime_error("Missing events tree");
  double norm=parameter(f,"pb_per_foam_weight");
  double fw=0,miss=0,py=0,e=0,eta=0,tr=0,ge=0,geta=0;
  auto bind=[&](const char* n,double* p){if(!tree->GetBranch(n))throw std::runtime_error(std::string("Missing branch: ")+n);tree->SetBranchAddress(n,p);};
  bind("foam_weight",&fw);bind("photon_miss_probability",&miss);bind("boson_py",&py);
  bind("electron_energy",&e);bind("electron_eta",&eta);bind("QA2",&tr);
  bind("boson_energy",&ge);bind("boson_eta",&geta);
  tree->SetBranchStatus("*",0);
  for(const char* n:{"foam_weight","photon_miss_probability","boson_py","electron_energy","electron_eta","QA2","boson_energy","boson_eta"})tree->SetBranchStatus(n,1);
  Group all,central,outside;long long mismatched_miss=0;
  double integrated_stored_sum=0;
  for(Long64_t j=0;j<tree->GetEntries();++j){
    tree->GetEntry(j);if(!(miss>0&&std::isfinite(fw)&&fw>=0))throw std::runtime_error("Invalid event weight or miss probability");
    double stored=fw*norm;integrated_stored_sum+=stored;
    double raw=already_effective?stored/miss:stored;
    double eff=already_effective?stored:stored*miss;
    bool out=std::abs(geta)>3.5;
    double expected=out?1.:1e-6;if(std::abs(miss/expected-1)>1e-10)++mismatched_miss;
    all.add(raw,eff,py,e,eta,tr,ge);(out?outside:central).add(raw,eff,py,e,eta,tr,ge);
  }
  std::cout<<std::setprecision(17)<<"{\"file\":"<<quote(path)<<",\"configuration\":"<<quote(description)
    <<",\"stored_weights_include_photon_loss\":"<<(already_effective?"true":"false")
    <<",\"attempts\":"<<attempts<<",\"stored_sigma_total_pb\":"<<parameter(f,"sigma_total_pb")
    <<",\"stored_sigma_error_pb\":"<<parameter(f,"sigma_total_error_pb")
    <<",\"reconstructed_stored_sigma_pb\":"<<integrated_stored_sum
    <<",\"miss_probability_mismatches\":"<<mismatched_miss<<",\"groups\":{\"all\":";
  all.write(attempts);std::cout<<",\"central\":";central.write(attempts);
  std::cout<<",\"outside\":";outside.write(attempts);std::cout<<"}}\n";
}
}
int main(int argc,char** argv){
  if(argc<2){std::cerr<<"Usage: diagnostics file.root [file.root ...]\n";return 2;}
  try{for(int j=1;j<argc;++j)diagnose(argv[j]);}
  catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
