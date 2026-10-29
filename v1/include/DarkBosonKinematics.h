#pragma once

#include <TLorentzVector.h>

namespace darkboson {

struct EventKinematics {
  TLorentzVector electron_in_lab;
  TLorentzVector ion_in_lab;
  TLorentzVector electron_out_lab;
  TLorentzVector ion_out_lab;
  TLorentzVector boson_lab;

  double t = 0.0;
  double m_e_boson = 0.0;
  double s_tilde = 0.0;
  double u_tilde = 0.0;
  double t2 = 0.0;
  double amplitude_reduced = 0.0;
  double density_pb = 0.0;

  double electron_q2() const {
    return -(electron_in_lab - electron_out_lab).M2();
  }

  bool finite() const;
};

struct PaperCut {
  double mass = 0.0;
  double qe2_min = 0.0;
  double pt_min = 0.0;
  double eta_min = 0.0;
  double eta_max = 0.0;
  double energy_max = 0.0;
};

PaperCut paper_cut_for_mass(double mass);
bool passes_paper_cut(const EventKinematics& event, double mass);

}  // namespace darkboson

