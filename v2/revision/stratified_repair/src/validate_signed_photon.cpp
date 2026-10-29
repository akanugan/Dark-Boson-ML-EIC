// Read-only signed-mirror restoration and schema validation.
#include <TFile.h>
#include <TTree.h>
#include <TLeaf.h>
#include <TBranch.h>
#include <TObjArray.h>
#include <TNamed.h>
#include <TParameter.h>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

double parameter(TFile& f,const char* name) {
  auto* p=dynamic_cast<TParameter<double>*>(f.Get(name));
  if (!p) throw std::runtime_error(std::string("Missing parameter ")+name);
  return p->GetVal();
}

int main(int argc,char** argv) {
  try {
    if (argc!=4) throw std::runtime_error("usage: validate_signed_photon new.root folded-pilot.root central-schema.root");
    TFile fresh(argv[1],"READ"),folded(argv[2],"READ"),central(argv[3],"READ");
    auto* a=dynamic_cast<TTree*>(fresh.Get("events"));
    auto* b=dynamic_cast<TTree*>(folded.Get("events"));
    auto* c=dynamic_cast<TTree*>(central.Get("events"));
    if (!a || !b || !c || fresh.IsZombie() || folded.IsZombie() || central.IsZombie())
      throw std::runtime_error("Missing ROOT event tree");
    bool schema=a->GetListOfBranches()->GetEntries()==c->GetListOfBranches()->GetEntries();
    for (int j=0;j<a->GetListOfBranches()->GetEntries();++j) {
      auto* branch=dynamic_cast<TBranch*>(a->GetListOfBranches()->At(j));
      auto* other=c->GetBranch(branch->GetName());
      if (!other || std::string(branch->GetTitle())!=other->GetTitle()) schema=false;
    }
    const auto n=a->GetEntries();
    if (n!=b->GetEntries()) throw std::runtime_error("Event count changed from folded baseline");
    long long invariant_mismatches=0,mirror_mismatches=0,loss_mismatches=0;
    double max_scalar_difference=0,sum=0,sum2=0,pos=0,neg=0;
    const double norm=parameter(fresh,"pb_per_foam_weight");
    for (Long64_t i=0;i<n;++i) {
      a->GetEntry(i);b->GetEntry(i);
      for (int j=0;j<a->GetListOfLeaves()->GetEntries();++j) {
        auto* leaf=dynamic_cast<TLeaf*>(a->GetListOfLeaves()->At(j));
        const std::string key=leaf->GetName();
        auto* prior=b->GetLeaf(key.c_str());
        if (!prior) throw std::runtime_error("Baseline leaf mismatch");
        const double current=leaf->GetValue(),old=prior->GetValue();
        if (!(std::isfinite(current) && std::isfinite(old))) throw std::runtime_error("Nonfinite event value");
        if (key=="electron_py" || key=="boson_py" || key=="ion_py") {
          if (std::abs(current)!=std::abs(old)) ++mirror_mismatches;
        } else {
          max_scalar_difference=std::max(max_scalar_difference,std::abs(current-old));
          if (current!=old) ++invariant_mismatches;
        }
      }
      const double py=a->GetLeaf("boson_py")->GetValue();
      const double oldpy=b->GetLeaf("boson_py")->GetValue();
      const double sign=py*oldpy<0 ? -1 : 1;
      for (const char* name : {"electron_py","ion_py"})
        if (a->GetLeaf(name)->GetValue()!=sign*b->GetLeaf(name)->GetValue()) ++mirror_mismatches;
      const double weight=norm*a->GetLeaf("foam_weight")->GetValue();
      if (!(weight>=0)) throw std::runtime_error("Negative weight");
      sum+=weight;sum2+=weight*weight;
      if (py>0) pos+=weight;
      if (py<0) neg+=weight;
      if (!(std::abs(a->GetLeaf("boson_eta")->GetValue())>3.5 &&
            a->GetLeaf("photon_miss_probability")->GetValue()==1 &&
            a->GetLeaf("pass_paper_cut")->GetValue()!=0)) ++loss_mismatches;
    }
    const double z=(pos-neg)/std::sqrt(sum2);
    const double sigma=parameter(fresh,"sigma_total_pb");
    const bool same_rate=sigma==parameter(folded,"sigma_total_pb");
    const bool same_norm=norm==parameter(folded,"pb_per_foam_weight");
    const double feature_difference=parameter(fresh,"mirror_max_feature_relative_difference");
    auto* config=dynamic_cast<TNamed*>(fresh.Get("generator_configuration"));
    const bool metadata=config && std::string(config->GetTitle()).find("signed_azimuth_distribution=full;")!=std::string::npos &&
        std::string(config->GetTitle()).find("mirror_restoration=independent_rng_after_weighted_selection")!=std::string::npos;
    const bool pass=schema && invariant_mismatches==0 && mirror_mismatches==0 &&
        loss_mismatches==0 && same_rate && same_norm && feature_difference==0 &&
        metadata && std::abs(z)<6 && std::abs(sum/sigma-1)<1e-10;
    std::cout << std::setprecision(17)
        << "{\"entries\":" << n << ",\"schema_matches_central\":" << (schema?"true":"false")
        << ",\"scalar_or_weight_mismatches\":" << invariant_mismatches
        << ",\"maximum_scalar_absolute_difference\":" << max_scalar_difference
        << ",\"mirror_mismatches\":" << mirror_mismatches
        << ",\"loss_or_selection_mismatches\":" << loss_mismatches
        << ",\"rate_identical_to_folded_pilot\":" << (same_rate?"true":"false")
        << ",\"normalization_identical_to_folded_pilot\":" << (same_norm?"true":"false")
        << ",\"runtime_feature_difference\":" << feature_difference
        << ",\"signed_metadata_valid\":" << (metadata?"true":"false")
        << ",\"positive_photon_y_weight_fraction\":" << pos/sum
        << ",\"mirror_weight_asymmetry_z\":" << z
        << ",\"reconstructed_sigma_pb\":" << sum
        << ",\"stored_sigma_pb\":" << sigma
        << ",\"passed\":" << (pass?"true":"false") << "}\n";
    return pass?0:2;
  } catch (const std::exception& error) {
    std::cerr << "Error: " << error.what() << '\n';
    return 1;
  }
}
