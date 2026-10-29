// Deterministic two-channel preimage/Jacobian check on stored physical points.
// No TFoam integration, event generation or training.
#define main cm_mixture_generator_entrypoint
#include "cm_mixture.cpp"
#undef main
#include <fstream>

int main() {
  bool all_passed=true,first=true;
  std::cout << std::setprecision(17)
      << "{\n  \"scope\":\"Deterministic full-support proposal and physical-point preimage identities; not integration convergence\",\n"
      << "  \"configurations\":[\n";
  for (int mass_index=0;mass_index<2;++mass_index) {
    const double mass=mass_index==0 ? .032 : 10.0;
    const auto box=mass_index==0 ? std::array<double,8>{{.74,.81,.02,.12,.08,.45,0,.25}}
                                : std::array<double,8>{{.74,.81,.06,.70,0,.09,0,.25}};
    GeneratorConfig cfg;
    cfg.mass=1e-6;cfg.cut_mass=mass;cfg.coupling=.3028221209;
    cfg.photon_region="forward";cfg.integrate_paper_cut=true;cfg.fold_phi=true;
    VectorBosonDensity baseline(cfg);
    cfg.cm_box_enabled=true;cfg.cm_box_probability=.75;cfg.cm_box=box;
    VectorBosonDensity mixture(cfg);
    const double p=cfg.cm_box_probability;
    double volume=1;
    for (int j=0;j<4;++j) volume*=box[2*j+1]-box[2*j];
    const double qin=1-p+p/volume;
    // Exact integral for the constant test density: outside uniform channel,
    // inside uniform channel, inside box channel. Overlap is counted once.
    const double constant_integral=(1-p)*(1-volume)/(1-p)+((1-p)*volume+p)/qin;
    std::ifstream input(mass_index==0 ? "revision_analysis/rate_benchmark/diagnostics_mapping_m0p032.csv"
                                    : "revision_analysis/rate_benchmark/diagnostics_mapping_m10p000.csv");
    if (!input) return 2;
    std::string line;
    std::getline(input,line);
    std::size_t checked=0,inside_count=0;
    double max_identity_error=0,max_t_error=0,max_energy_error=0;
    while (std::getline(input,line)) {
      std::istringstream tokens(line);
      std::vector<double> columns;
      std::string token;
      while (std::getline(tokens,token,',')) columns.push_back(std::stod(token));
      if (columns.size()!=23) return 3;
      std::array<double,4> y{{columns[18],columns[19],columns[20],
                              2*std::min(columns[21],1-columns[21])}};
      darkboson::EventKinematics base_event, uniform_event,box_event;
      double f=0,gu=0,gb=0;
      if (!baseline.build_event(y.data(),base_event,f) || !(f>0)) return 4;
      std::array<double,4> uniform=y;
      uniform[0]=p+(1-p)*y[0];
      if (!mixture.build_event(uniform.data(),uniform_event,gu)) return 5;
      bool inside=true;
      for (int j=0;j<4;++j) inside=inside && y[j]>=box[2*j] && y[j]<=box[2*j+1];
      double reconstructed=gu*(1-p);
      if (inside) {
        std::array<double,4> boxed;
        for (int j=0;j<4;++j) boxed[j]=(y[j]-box[2*j])/(box[2*j+1]-box[2*j]);
        boxed[0]*=p;
        if (!mixture.build_event(boxed.data(),box_event,gb)) return 6;
        reconstructed+=gb*p/volume;
        max_t_error=std::max(max_t_error,std::abs(box_event.t/base_event.t-1));
        max_energy_error=std::max(max_energy_error,std::abs(box_event.electron_out_lab.E()-base_event.electron_out_lab.E()));
        ++inside_count;
      }
      max_identity_error=std::max(max_identity_error,std::abs(reconstructed/f-1));
      max_t_error=std::max(max_t_error,std::abs(uniform_event.t/base_event.t-1));
      max_energy_error=std::max(max_energy_error,std::abs(uniform_event.electron_out_lab.E()-base_event.electron_out_lab.E()));
      ++checked;
    }
    const bool pass=checked==100 && std::abs(constant_integral-1)<1e-12 && max_identity_error<1e-5;
    all_passed=all_passed && pass;
    if (!first) std::cout << ",\n";
    first=false;
    std::cout << "    {\"mass_GeV\":" << mass << ",\"box_volume\":" << volume
        << ",\"uniform_probability\":" << 1-p << ",\"inside_proposal_density\":" << qin
        << ",\"constant_integral\":" << constant_integral
        << ",\"physical_points\":" << checked << ",\"inside_box_points\":" << inside_count
        << ",\"max_preimage_density_identity_relative_error\":" << max_identity_error
        << ",\"max_t_roundtrip_relative_error\":" << max_t_error
        << ",\"max_electron_energy_difference_GeV\":" << max_energy_error
        << ",\"passed\":" << (pass?"true":"false") << "}";
  }
  std::cout << "\n  ],\n  \"passed\":" << (all_passed?"true":"false") << "\n}\n";
  return all_passed ? 0 : 7;
}
