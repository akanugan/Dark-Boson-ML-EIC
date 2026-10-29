// Deterministic coordinate-identity checks; no TFoam integration or event generation.
#define main lab_diagnostic_generator_entrypoint
#include "lab_transformed.cpp"
#undef main

int main() {
  std::size_t checked = 0;
  double max_reflection_relative = 0.0;
  double max_fold_relative = 0.0;
  double max_log_jacobian_relative = 0.0;
  double max_energy_difference = 0.0;
  for (double cut_mass : {0.01, 10.0}) {
    GeneratorConfig cfg;
    cfg.mass = 1e-6;
    cfg.cut_mass = cut_mass;
    cfg.coupling = 0.3028221209;
    cfg.photon_region = "outside";
    cfg.integrate_paper_cut = true;
    VectorBosonDensity full(cfg);
    cfg.fold_phi = true;
    VectorBosonDensity folded(cfg);
    cfg.log_electron_energy = true;
    VectorBosonDensity folded_log(cfg);
    for (double a : {0.15, 0.35, 0.55, 0.75, 0.95}) {
      for (double b : {0.05, 0.2, 0.5, 0.8}) {
        for (double c : {0.05, 0.2, 0.35, 0.45, 0.8}) {
          for (double d : {0.2, 0.5, 0.8, 0.95, 0.99}) {
            std::array<double,4> x{{a,b,c,d/2}};
            darkboson::EventKinematics event, mirror, fevent, levent;
            double v=0,mv=0,fv=0,lv=0;
            if (!full.build_event(x.data(),event,v) || !(v>1e-50)) continue;
            x[3] = 1-d/2;
            if (!full.build_event(x.data(),mirror,mv)) return 2;
            max_reflection_relative = std::max(max_reflection_relative,
                                               std::abs(mv/v-1));
            x[3] = d;
            if (!folded.build_event(x.data(),fevent,fv)) return 3;
            max_fold_relative = std::max(max_fold_relative,std::abs(fv/v-1));
            const auto cut = darkboson::paper_cut_for_mass(cut_mass);
            const double eta = event.electron_out_lab.Eta();
            const double emin = std::sqrt(kElectronMass*kElectronMass+
                std::pow(cut.pt_min*std::cosh(eta),2));
            const double energy = event.electron_out_lab.E();
            const double log_span = std::log(cut.energy_max/emin);
            x[1] = std::log(energy/emin)/log_span;
            if (!folded_log.build_event(x.data(),levent,lv)) return 4;
            const double expected_ratio = energy*log_span/(cut.energy_max-emin);
            max_log_jacobian_relative = std::max(max_log_jacobian_relative,
                                                std::abs(lv/(v*expected_ratio)-1));
            max_energy_difference = std::max(max_energy_difference,
                std::abs(levent.electron_out_lab.E()-energy));
            ++checked;
          }
        }
      }
    }
  }
  std::cout << std::setprecision(17)
      << "{\n  \"scope\": \"Deterministic coordinate identities only; no integration, convergence or physical-model claim\",\n"
      << "  \"checked_nonzero_points\": " << checked << ",\n"
      << "  \"max_reflection_relative\": " << max_reflection_relative << ",\n"
      << "  \"max_fold_relative\": " << max_fold_relative << ",\n"
      << "  \"max_log_jacobian_relative\": " << max_log_jacobian_relative << ",\n"
      << "  \"max_energy_difference_GeV\": " << max_energy_difference << "\n}\n";
  return checked>0 && max_reflection_relative<1e-5 &&
      max_fold_relative<1e-12 && max_log_jacobian_relative<1e-5 ? 0 : 5;
}
