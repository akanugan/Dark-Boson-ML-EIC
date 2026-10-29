// Direct IID integration of the exact full-support CM mixture. No adaptation.
// The included diagnostic supplies the unchanged physical integrand, mapping,
// CLI and metadata; its TFoam main is renamed and never executed here.
#define main unused_cm_mixture_adaptive_entrypoint
#include "cm_mixture.cpp"
#undef main

#include <fstream>
#include <memory>

#ifndef IID_SOURCE_SHA256
#define IID_SOURCE_SHA256 "not_embedded"
#endif

namespace {

struct IidMoments {
  long long n=0;
  long double mean=0,m2=0,sum_square=0;
  void add(double value) {
    ++n;
    const long double v=value;
    const long double delta=v-mean;
    mean+=delta/n;
    m2+=delta*(v-mean);
    sum_square+=v*v;
  }
  double sem() const {
    return n>1 ? std::sqrt(static_cast<double>(m2/(static_cast<long double>(n)*(n-1)))) : 0;
  }
};

bool moments_self_check() {
  IidMoments m;
  for (double v : {0.,1.,2.,3.}) m.add(v);
  // Unbiased variance=5/3; SEM=sqrt((5/3)/4). Both zeros and nonzeros count.
  return m.n==4 && std::abs(static_cast<double>(m.mean)-1.5)<1e-15 &&
      std::abs(m.sem()-std::sqrt(5.0/12.0))<1e-15;
}

}  // namespace

int main(int argc,char** argv) {
  try {
    bool save_events=false,self_check=false;
    std::string rate_json;
    std::vector<char*> standard_args;
    standard_args.push_back(argv[0]);
    for (int i=1;i<argc;++i) {
      const std::string option=argv[i];
      if (option=="--save-events") save_events=true;
      else if (option=="--iid-self-check") self_check=true;
      else if (option=="--rate-json") {
        if (i+1>=argc) throw std::runtime_error("Missing path after --rate-json");
        rate_json=argv[++i];
      } else standard_args.push_back(argv[i]);
    }
    if (!moments_self_check()) throw std::runtime_error("IID moment/zero-count self-check failed");
    if (self_check) {
      std::cout << "iid_moments_self_check=passed\nzeros_included=1\n";
      return 0;
    }
    for (char* argument : standard_args) {
      if (std::string(argument)=="--help" || std::string(argument)=="-h") {
        print_help(argv[0]);
        std::cout << "  --rate-json path           Optional JSON rate/metadata summary\n"
                  << "  --save-events              Optional diagnostic ROOT event output; default rate only\n"
                  << "  --iid-self-check           Check ordinary IID mean and SEM including zeros\n\n"
                  << "IID: --events counts ALL uniform unit-cube attempts, including zero-density points.\n"
                  << "--cells/--samples are parsed for compatibility but not used; no TFoam adaptation occurs.\n";
        return 0;
      }
    }
    const auto cfg=parse_arguments(static_cast<int>(standard_args.size()),standard_args.data());
    if (cfg.events<2) throw std::runtime_error("IID SEM requires at least two attempts");
    VectorBosonDensity density(cfg);
    TRandom3 random(cfg.seed);
    if (cfg.fold_phi) {
      std::cerr << "IID DIAGNOSTIC: azimuth mirrors integrated analytically; stored signed y represents one mirror only.\n";
    }

    std::unique_ptr<TFile> output;
    std::unique_ptr<TTree> events;
    Long64_t attempt=0;
    double value=0,weight_pb=0,e_energy=0,e_eta=0,e_pt=0,qe2=0,t=0;
    double gamma_energy=0,gamma_eta=0,gamma_py=0;
    if (save_events) {
      const std::filesystem::path path(cfg.output);
      if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path());
      output=std::make_unique<TFile>(cfg.output.c_str(),"RECREATE");
      if (output->IsZombie()) throw std::runtime_error("Could not create output: "+cfg.output);
      events=std::make_unique<TTree>("events","Direct IID weighted CM-mixture diagnostic points");
      events->SetDirectory(nullptr);
      events->Branch("attempt",&attempt);
      events->Branch("iid_integrand_pb",&value);
      events->Branch("event_weight_pb",&weight_pb);
      events->Branch("electron_energy",&e_energy);
      events->Branch("electron_eta",&e_eta);
      events->Branch("electron_pt",&e_pt);
      events->Branch("Qe2",&qe2);
      events->Branch("QA2",&t);
      events->Branch("boson_energy",&gamma_energy);
      events->Branch("boson_eta",&gamma_eta);
      events->Branch("boson_py",&gamma_py);
    }

    IidMoments moments;
    long long accepted=0,zero=0;
    double largest=0;
    std::array<double,4> x;
    for (attempt=0;attempt<cfg.events;++attempt) {
      for (double& coordinate : x) coordinate=random.Rndm();
      darkboson::EventKinematics event;
      value=0;
      const bool valid=density.build_event(x.data(),event,value);
      // Identical zero-valued rejection as the original deterministic callback.
      // Every rejected point still enters the IID denominator and variance.
      if (!valid) value=0;
      if (!(std::isfinite(value) && value>=0)) {
        throw std::runtime_error("Nonfinite or negative successful IID integrand");
      }
      moments.add(value);
      largest=std::max(largest,value);
      if (value>0) {
        ++accepted;
        if (events) {
          weight_pb=value/cfg.events;
          e_energy=event.electron_out_lab.E();e_eta=event.electron_out_lab.Eta();
          e_pt=event.electron_out_lab.Pt();qe2=event.electron_q2();t=event.t;
          gamma_energy=event.boson_lab.E();gamma_eta=event.boson_lab.Eta();
          gamma_py=event.boson_lab.Py();
          events->Fill();
        }
      } else ++zero;
      if (!cfg.quiet && (attempt+1)%1000000==0) {
        std::cerr << "iid_attempts=" << attempt+1 << " positive=" << accepted
                  << " mean_pb=" << static_cast<double>(moments.mean)
                  << " sem_pb=" << moments.sem() << "\n";
      }
    }
    const double sigma=static_cast<double>(moments.mean),error=moments.sem();
    const long double sum=moments.mean*moments.n;
    const double neff=moments.sum_square>0 ? static_cast<double>(sum*sum/moments.sum_square) : 0;
    const double largest_fraction=sum>0 ? static_cast<double>(largest/sum) : 0;
    std::ostringstream config;
    config << configuration_string(cfg,density)
           << ";integration_method=direct_iid_uniform_cube;adaptation=none"
           << ";zero_density_points_included=1;iid_error=unbiased_sample_sem"
           << ";iid_source_sha256=" << IID_SOURCE_SHA256;
    if (output) {
      output->cd();events->Write();
      TNamed metadata("generator_configuration",config.str().c_str());metadata.Write();
      TParameter<double> rate("sigma_total_pb",sigma);rate.Write();
      TParameter<double> sem("sigma_total_error_pb",error);sem.Write();
      TParameter<Long64_t> attempts("iid_attempts",cfg.events);attempts.Write();
      TParameter<Long64_t> positive("accepted_events",accepted);positive.Write();
      output->Close();
    }
    std::cout << std::setprecision(12)
        << "integration_method=direct_iid_uniform_cube\n"
        << "attempted_events=" << cfg.events << "\naccepted_events=" << accepted
        << "\nzero_density_events=" << zero
        << "\nsigma_total_pb=" << sigma << " +/- " << error
        << "\niid_effective_sample_size=" << neff
        << "\nlargest_weight_fraction=" << largest_fraction
        << "\nzero_support_warning=" << (accepted==0?1:0)
        << "\noutput=" << (save_events?cfg.output:"none_rate_only") << "\n";
    if (!rate_json.empty()) {
      const std::filesystem::path path(rate_json);
      if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path());
      std::ofstream json(path);
      if (!json) throw std::runtime_error("Could not create summary: "+rate_json);
      // configuration_string contains no JSON quotes or control characters.
      json << std::setprecision(17)
          << "{\n  \"method\":\"direct_iid_uniform_cube_no_adaptation\",\n"
          << "  \"attempts\":" << cfg.events << ",\n  \"positive_points\":" << accepted
          << ",\n  \"zero_points\":" << zero
          << ",\n  \"sigma_total_pb\":" << sigma
          << ",\n  \"sigma_total_error_pb\":" << error
          << ",\n  \"effective_sample_size\":" << neff
          << ",\n  \"largest_weight_fraction\":" << largest_fraction
          << ",\n  \"zero_support_warning\":" << (accepted==0?"true":"false")
          << ",\n  \"error_scope\":\"Ordinary IID SEM includes zero-valued attempts; finite sampling does not bound unobserved tails or physical-model uncertainty\""
          << ",\n  \"configuration\":\"" << config.str() << "\"\n}\n";
    }
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Error: " << error.what() << "\n";
    return 1;
  }
}
