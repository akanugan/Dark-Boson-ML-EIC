#include <TFile.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TTree.h>

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

struct Cut {
  double qe2_min = 0.0;
  double pt_min = 0.0;
  double eta_min = 0.0;
  double eta_max = 0.0;
  double energy_max = 0.0;
};

Cut read_cut(const std::string& csv_path, double target_mass) {
  std::ifstream input(csv_path);
  if (!input) throw std::runtime_error("cannot open cuts: " + csv_path);
  std::string line;
  std::getline(input, line);
  Cut best;
  double best_distance = 1e99;
  while (std::getline(input, line)) {
    if (line.empty()) continue;
    for (char& c : line) if (c == ',') c = ' ';
    std::istringstream row(line);
    double mass = 0.0, photon = 0.0, dis = 0.0;
    Cut cut;
    if (!(row >> mass >> cut.qe2_min >> cut.pt_min >> cut.eta_min >>
          cut.eta_max >> cut.energy_max >> photon >> dis)) continue;
    const double distance = std::abs(std::log(mass / target_mass));
    if (distance < best_distance) {
      best_distance = distance;
      best = cut;
    }
  }
  if (!std::isfinite(best_distance)) throw std::runtime_error("no cut row found");
  return best;
}

template <typename T>
T read_parameter(TFile& file, const char* name) {
  auto* p = dynamic_cast<TParameter<T>*>(file.Get(name));
  if (!p) throw std::runtime_error(std::string("missing parameter: ") + name);
  return p->GetVal();
}

void usage(const char* program) {
  std::cerr << "Usage: " << program
            << " input.root signal cuts.csv cutflow.csv events.csv split_seed\n";
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 7) {
      usage(argv[0]);
      return 2;
    }
    const std::string input_path = argv[1];
    const std::string signal = argv[2];
    const std::string cuts_path = argv[3];
    const std::string cutflow_path = argv[4];
    const std::string events_path = argv[5];
    const unsigned long long split_seed = std::stoull(argv[6]);

    TFile file(input_path.c_str(), "READ");
    if (file.IsZombie()) throw std::runtime_error("cannot open ROOT file");
    auto* tree = dynamic_cast<TTree*>(file.Get("events"));
    if (!tree) throw std::runtime_error("missing events tree");

    Long64_t event = 0;
    double foam_weight = 0.0, mass = 0.0, coupling = 0.0;
    double electron_pt = 0.0, electron_eta = 0.0, electron_energy = 0.0;
    double qe2 = 0.0, qa2 = 0.0, pair_mass = 0.0;
    tree->SetBranchAddress("event", &event);
    tree->SetBranchAddress("foam_weight", &foam_weight);
    tree->SetBranchAddress("mass", &mass);
    tree->SetBranchAddress("coupling", &coupling);
    tree->SetBranchAddress("electron_pt", &electron_pt);
    tree->SetBranchAddress("electron_eta", &electron_eta);
    tree->SetBranchAddress("electron_energy", &electron_energy);
    tree->SetBranchAddress("Qe2", &qe2);
    tree->SetBranchAddress("QA2", &qa2);
    tree->SetBranchAddress("pair_mass", &pair_mass);

    if (tree->GetEntries() == 0) throw std::runtime_error("empty event tree");
    tree->GetEntry(0);
    const Cut cut = read_cut(cuts_path, mass);
    const double sigma_total = read_parameter<double>(file, "sigma_total_pb");
    const double sigma_error = read_parameter<double>(file, "sigma_total_error_pb");
    const double pb_per_weight = read_parameter<double>(file, "pb_per_foam_weight");

    long double sum_all = 0.0L, sum_qe2 = 0.0L, sum_pt = 0.0L;
    long double sum_eta = 0.0L, sum_energy = 0.0L;
    long double sum2_all = 0.0L, sum2_qe2 = 0.0L, sum2_pt = 0.0L;
    long double sum2_eta = 0.0L, sum2_energy = 0.0L;
    long long count_all = 0, count_qe2 = 0, count_pt = 0, count_eta = 0, count_energy = 0;

    std::ofstream events_out(events_path);
    if (!events_out) throw std::runtime_error("cannot create events CSV");
    events_out << "event_id,process,signal_type,mass_GeV,coupling,event_weight_pb,"
                  "electron_pt_GeV,electron_eta,electron_energy_GeV,Qe2_GeV2,QA2_GeV2,"
                  "pair_mass_GeV,pass_Qe2,pass_pt,pass_eta,pass_energy,pass_all,split\n";
    events_out << std::setprecision(12);

    const Long64_t entries = tree->GetEntries();
    for (Long64_t i = 0; i < entries; ++i) {
      tree->GetEntry(i);
      const bool p_qe2 = qe2 > cut.qe2_min;
      const bool p_pt = electron_pt > cut.pt_min;
      const bool p_eta = electron_eta > cut.eta_min && electron_eta < cut.eta_max;
      const bool p_energy = electron_energy < cut.energy_max;
      const bool p_all = p_qe2 && p_pt && p_eta && p_energy;
      const long double w = foam_weight;
      ++count_all; sum_all += w; sum2_all += w * w;
      if (p_qe2) { ++count_qe2; sum_qe2 += w; sum2_qe2 += w * w; }
      if (p_qe2 && p_pt) { ++count_pt; sum_pt += w; sum2_pt += w * w; }
      if (p_qe2 && p_pt && p_eta) { ++count_eta; sum_eta += w; sum2_eta += w * w; }
      if (p_all) { ++count_energy; sum_energy += w; sum2_energy += w * w; }

      unsigned long long x = static_cast<unsigned long long>(event) + split_seed;
      x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL;
      x ^= x >> 27; x *= 0x94d049bb133111ebULL;
      x ^= x >> 31;
      const unsigned bucket = static_cast<unsigned>(x % 100ULL);
      const char* split = bucket < 70 ? "train" : (bucket < 85 ? "validation" : "test");

      events_out << signal << '_' << std::fixed << std::setprecision(3) << mass << '_'
                 << event << ",signal," << signal << ',' << std::setprecision(12)
                 << mass << ',' << coupling << ',' << static_cast<double>(w) * pb_per_weight
                 << ',' << electron_pt << ',' << electron_eta << ',' << electron_energy
                 << ',' << qe2 << ',' << qa2 << ',' << pair_mass << ',' << p_qe2 << ','
                 << p_pt << ',' << p_eta << ',' << p_energy << ',' << p_all << ',' << split << '\n';
    }

    std::ofstream cutflow(cutflow_path);
    if (!cutflow) throw std::runtime_error("cannot create cutflow CSV");
    cutflow << "signal_type,mass_GeV,stage,raw_events,sum_weights,sum_weights_squared,"
               "effective_events,weighted_cross_section_pb,cumulative_efficiency,"
               "incremental_efficiency,sigma_total_error_pb\n";
    cutflow << std::setprecision(12);
    const long double stages[] = {sum_all, sum_qe2, sum_pt, sum_eta, sum_energy};
    const long double stages2[] = {sum2_all, sum2_qe2, sum2_pt, sum2_eta, sum2_energy};
    const long long counts[] = {count_all, count_qe2, count_pt, count_eta, count_energy};
    const char* names[] = {"inclusive", "Qe2", "Qe2+pt", "Qe2+pt+eta", "all_Table_I_cuts"};
    for (int i = 0; i < 5; ++i) {
      const double xs = i == 0 ? sigma_total : static_cast<double>(stages[i] * pb_per_weight);
      const double cumulative = sum_all > 0.0L ? static_cast<double>(stages[i] / sum_all) : 0.0;
      const double incremental = i == 0 ? 1.0 : (stages[i-1] > 0.0L ? static_cast<double>(stages[i] / stages[i-1]) : 0.0);
      const double effective = stages2[i] > 0.0L
        ? static_cast<double>(stages[i] * stages[i] / stages2[i]) : 0.0;
      cutflow << signal << ',' << mass << ',' << names[i] << ',' << counts[i] << ','
              << static_cast<double>(stages[i]) << ',' << static_cast<double>(stages2[i])
              << ',' << effective << ',' << xs << ',' << cumulative << ','
              << incremental << ',' << sigma_error << '\n';
    }
    std::cout << signal << " m=" << mass << " GeV: " << sigma_total << " -> "
              << static_cast<double>(sum_energy * pb_per_weight) << " pb\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
