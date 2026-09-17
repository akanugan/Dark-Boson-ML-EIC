#include <TFile.h>
#include <TParameter.h>
#include <TTree.h>

#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::vector<std::pair<double, double>> read_histogram(const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path);
  std::vector<std::pair<double, double>> result;
  double x = 0.0, y = 0.0;
  while (input >> x >> y) result.emplace_back(x, y);
  return result;
}

double total(const std::vector<std::pair<double, double>>& histogram) {
  double sum = 0.0;
  for (const auto& bin : histogram) sum += bin.second;
  return sum;
}

void compare(const std::string& name,
             const std::vector<std::pair<double, double>>& published,
             const std::vector<double>& our_model, std::ostream& output) {
  const double published_sum = total(published);
  double our_model_sum = 0.0;
  for (double value : our_model) our_model_sum += value;
  double l1 = 0.0;
  output << "observable,left_edge,published_probability,our_model_probability\n";
  for (size_t i = 0; i < published.size(); ++i) {
    const double p = published_sum > 0.0 ? published[i].second / published_sum : 0.0;
    const double q = our_model_sum > 0.0 ? our_model[i] / our_model_sum : 0.0;
    l1 += std::abs(p - q);
    output << name << ',' << published[i].first << ',' << p << ',' << q << '\n';
  }
  std::cerr << name << " total_variation_distance=" << 0.5 * l1 << '\n';
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 5) return 2;
  TFile file(argv[1], "READ");
  auto* tree = dynamic_cast<TTree*>(file.Get("events"));
  if (!tree) return 1;
  const auto pt = read_histogram(argv[2]);
  const auto eta = read_histogram(argv[3]);
  std::vector<double> pt_bins(pt.size(), 0.0), eta_bins(eta.size(), 0.0);
  double weight = 0.0, electron_pt = 0.0, electron_eta = 0.0;
  tree->SetBranchAddress("foam_weight", &weight);
  tree->SetBranchAddress("electron_pt", &electron_pt);
  tree->SetBranchAddress("electron_eta", &electron_eta);
  for (Long64_t i = 0; i < tree->GetEntries(); ++i) {
    tree->GetEntry(i);
    const double log_pt = std::log10(std::max(electron_pt, 1.0e-99));
    for (size_t b = 0; b < pt.size(); ++b) {
      const double high = b + 1 < pt.size() ? pt[b + 1].first : pt[b].first + 0.5;
      if (log_pt >= pt[b].first && log_pt < high) { pt_bins[b] += weight; break; }
    }
    for (size_t b = 0; b < eta.size(); ++b) {
      const double high = b + 1 < eta.size() ? eta[b + 1].first : eta[b].first + 1.0;
      if (electron_eta >= eta[b].first && electron_eta < high) { eta_bins[b] += weight; break; }
    }
  }
  std::ofstream output(argv[4]);
  output << std::setprecision(12);
  compare("log10_electron_pt", pt, pt_bins, output);
  output << '\n';
  compare("electron_eta", eta, eta_bins, output);
  return 0;
}
