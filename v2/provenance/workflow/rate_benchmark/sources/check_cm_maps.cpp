// Deterministic physical-point map checks; no TFoam integration or generation.
#define main cm_diagnostic_generator_entrypoint
#include "cm_transformed.cpp"
#undef main

int main() {
  GeneratorConfig cfg;
  cfg.mass = 1e-6;
  cfg.cut_mass = 0.032;
  cfg.coupling = 0.3028221209;
  cfg.photon_region = "all";
  cfg.integrate_paper_cut = false;
  VectorBosonDensity full(cfg);
  cfg.fold_phi = true;
  VectorBosonDensity folded(cfg);
  cfg.log_pair_mass = true;
  VectorBosonDensity folded_log(cfg);
  std::size_t checked=0, selected_low=0, selected_high=0;
  double max_reflection_relative=0, max_fold_relative=0;
  double max_log_jacobian_relative=0, max_mass_difference=0;
  double max_log_low=0, max_log_high=0;
  double worst_mass=0, worst_t=0, worst_qe2=0, worst_energy=0, worst_density=0;
  std::array<double,4> worst_point{};
  const double min_mass = kElectronMass + cfg.mass;
  for (double a : {0.45,0.55,0.65,0.7,0.75,0.8,0.85}) {
    for (double b : {0.00001,0.0001,0.001,0.01,0.1,0.3,0.7}) {
      for (double c : {0.05,0.25,0.5,0.75,0.95}) {
        for (double d : {0.1,0.3,0.5,0.75,0.95}) {
          std::array<double,4> x{{a,b,c,d/2}};
          darkboson::EventKinematics event, mirror, fevent, levent;
          double v=0,mv=0,fv=0,lv=0;
          if (!full.build_event(x.data(),event,v) || !(v>1e-50) ||
              event.t<1e-9) continue;
          x[3]=1-d/2;
          if (!full.build_event(x.data(),mirror,mv)) return 2;
          max_reflection_relative=std::max(max_reflection_relative,
                                           std::abs(mv/v-1));
          x[3]=d;
          if (!folded.build_event(x.data(),fevent,fv)) return 3;
          max_fold_relative=std::max(max_fold_relative,std::abs(fv/v-1));
          const double mass = event.m_e_boson;
          // Recover the same t-dependent upper endpoint from the original
          // linear map without exposing or changing generator internals.
          const double max_mass = min_mass+(mass-min_mass)/b;
          const double log_span=std::log(max_mass/min_mass);
          x[1]=std::log(mass/min_mass)/log_span;
          if (!folded_log.build_event(x.data(),levent,lv)) return 4;
          const double expected_ratio=mass*log_span/(max_mass-min_mass);
          const double discrepancy=std::abs(lv/(v*expected_ratio)-1);
          if (discrepancy>max_log_jacobian_relative) {
            max_log_jacobian_relative=discrepancy;
            worst_mass=mass; worst_t=event.t;
            worst_qe2=event.electron_q2(); worst_energy=event.electron_out_lab.E();
            worst_density=v;
            worst_point={{a,b,c,d/2}};
          }
          if (darkboson::passes_paper_cut(event,0.032)) {
            ++selected_low; max_log_low=std::max(max_log_low,discrepancy);
          }
          if (darkboson::passes_paper_cut(event,10.0)) {
            ++selected_high; max_log_high=std::max(max_log_high,discrepancy);
          }
          max_mass_difference=std::max(max_mass_difference,
                                        std::abs(levent.m_e_boson-mass));
          ++checked;
        }
      }
    }
  }
  std::cout << std::setprecision(17)
      << "{\n  \"scope\": \"Selected-rate coordinate identities; unrestricted precision warning retained; no integration or convergence claim\",\n"
      << "  \"checked_nonzero_points\": " << checked << ",\n"
      << "  \"minimum_checked_t_GeV2\": 1e-9,\n"
      << "  \"max_reflection_relative\": " << max_reflection_relative << ",\n"
      << "  \"max_fold_relative\": " << max_fold_relative << ",\n"
      << "  \"max_log_jacobian_relative\": " << max_log_jacobian_relative << ",\n"
      << "  \"unrestricted_precision_warning\": "
      << (max_log_jacobian_relative>=1e-5 ? "true" : "false") << ",\n"
      << "  \"max_pair_mass_difference_GeV\": " << max_mass_difference << ",\n"
      << "  \"selected_low_points\": " << selected_low << ",\n"
      << "  \"selected_high_points\": " << selected_high << ",\n"
      << "  \"max_log_jacobian_relative_selected_low\": " << max_log_low << ",\n"
      << "  \"max_log_jacobian_relative_selected_high\": " << max_log_high << ",\n"
      << "  \"worst_point\": [" << worst_point[0] << "," << worst_point[1] << ","
      << worst_point[2] << "," << worst_point[3] << "],\n"
      << "  \"worst_pair_mass_GeV\": " << worst_mass << ",\n"
      << "  \"worst_t_GeV2\": " << worst_t << ",\n"
      << "  \"worst_electron_qe2_GeV2\": " << worst_qe2 << ",\n"
      << "  \"worst_electron_energy_GeV\": " << worst_energy << ",\n"
      << "  \"worst_density_pb\": " << worst_density << "\n}\n";
  // Acceptance is explicitly for the selected rates under investigation.
  // The unrestricted ultrasoft/collinear warning above remains in the output;
  // it does not justify claiming general high-precision mass-map invariance.
  return checked>0 && selected_low>0 && selected_high>0 &&
      max_reflection_relative<1e-5 && max_fold_relative<1e-12 &&
      max_log_low<1e-5 && max_log_high<1e-5 ? 0 : 5;
}
