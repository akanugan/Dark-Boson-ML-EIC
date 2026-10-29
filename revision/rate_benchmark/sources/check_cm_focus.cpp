// Deterministic full-domain t-map and selected density/Jacobian identities.
// No TFoam integration, model fitting or Monte Carlo event generation.
#define main cm_focused_generator_entrypoint
#include "cm_focused.cpp"
#undef main

int main() {
  GeneratorConfig cfg;
  cfg.mass=1e-6; cfg.cut_mass=.032; cfg.coupling=.3028221209;
  cfg.photon_region="all"; cfg.integrate_paper_cut=false;
  cfg.log_pair_mass=true; cfg.fold_phi=true;
  VectorBosonDensity baseline(cfg);
  std::cout << std::setprecision(17)
      << "{\n  \"scope\": \"Deterministic selected-rate coordinate and Jacobian identities; not integration convergence\",\n"
      << "  \"configurations\": [\n";
  bool first=true, passed=true;
  for (const auto spec : {std::array<double,2>{{.1,1.5}},
                          std::array<double,2>{{1e-4,3.0}}}) {
    cfg.t_importance_center=spec[0]; cfg.t_importance_width=spec[1];
    VectorBosonDensity focused(cfg);
    const double tmin=baseline.t_min(), tmax=baseline.t_max();
    const double logc=std::log(spec[0]), width=spec[1];
    const double alo=std::atan((std::log(tmin)-logc)/width);
    const double ahi=std::atan((std::log(tmax)-logc)/width);
    const double span=ahi-alo, logratio=std::log(tmax/tmin);
    const double endpoint_low=std::exp(logc+width*std::tan(alo));
    const double endpoint_high=std::exp(logc+width*std::tan(ahi));
    const double endpoint_error=std::max(std::abs(endpoint_low/tmin-1),
                                         std::abs(endpoint_high/tmax-1));
    bool monotonic=true;
    double previous=0;
    for (int i=0;i<=1000;++i) {
      const double t=std::exp(logc+width*std::tan(alo+span*i/1000.0));
      if (!(std::isfinite(t) && t>previous)) monotonic=false;
      previous=t;
    }
    std::size_t low_count=0, high_count=0;
    double max_low=0,max_high=0,max_t_diff=0,max_energy_diff=0;
    for (double a : {.45,.55,.6,.65,.7,.75,.8,.85}) {
      for (double b : {.1,.25,.4,.55,.7,.85,.95}) {
        for (double c : {.05,.25,.5,.75,.95}) {
          for (double d : {.1,.3,.5,.75,.95}) {
            std::array<double,4> x{{a,b,c,d}};
            darkboson::EventKinematics event, check;
            double value=0,focused_value=0;
            if (!baseline.build_event(x.data(),event,value) || !(value>1e-50)) continue;
            const bool low=darkboson::passes_paper_cut(event,.032);
            const bool high=darkboson::passes_paper_cut(event,10.0);
            if (!(low || high)) continue;
            const double scaled_log=(std::log(event.t)-logc)/width;
            const double angle=std::atan(scaled_log);
            x[0]=(angle-alo)/span;
            if (!focused.build_event(x.data(),check,focused_value)) return 2;
            const double ratio=width*span*(1+scaled_log*scaled_log)/logratio;
            const double discrepancy=std::abs(focused_value/(value*ratio)-1);
            if (low) { ++low_count; max_low=std::max(max_low,discrepancy); }
            if (high) { ++high_count; max_high=std::max(max_high,discrepancy); }
            max_t_diff=std::max(max_t_diff,std::abs(check.t/event.t-1));
            max_energy_diff=std::max(max_energy_diff,
                std::abs(check.electron_out_lab.E()-event.electron_out_lab.E()));
          }
        }
      }
    }
    if (!first) std::cout << ",\n";
    first=false;
    std::cout << "    {\"center_GeV2\":" << spec[0] << ",\"width\":" << width
        << ",\"endpoint_max_relative_error\":" << endpoint_error
        << ",\"monotonic\":" << (monotonic ? "true" : "false")
        << ",\"selected_low_points\":" << low_count
        << ",\"selected_high_points\":" << high_count
        << ",\"max_density_jacobian_relative_selected_low\":" << max_low
        << ",\"max_density_jacobian_relative_selected_high\":" << max_high
        << ",\"max_t_relative_difference\":" << max_t_diff
        << ",\"max_electron_energy_difference_GeV\":" << max_energy_diff << "}";
    passed=passed && endpoint_error<1e-10 && monotonic && low_count>0 && high_count>0
        && max_low<1e-5 && max_high<1e-5;
  }
  std::cout << "\n  ],\n  \"passed\":" << (passed ? "true" : "false") << "\n}\n";
  return passed ? 0 : 5;
}
