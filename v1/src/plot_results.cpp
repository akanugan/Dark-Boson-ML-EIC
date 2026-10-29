#include <TCanvas.h>
#include <TColor.h>
#include <TGraph.h>
#include <TGraphErrors.h>
#include <TH1D.h>
#include <TLegend.h>
#include <TLine.h>
#include <TMultiGraph.h>
#include <TStyle.h>
#include <TLatex.h>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct Metric {
  std::string type;
  double mass = 0.0, auc = 0.0, signal_efficiency = 0.0;
  double background_efficiency = 0.0, improvement = 0.0;
  double improvement_error = 0.0, coupling_improvement = 0.0;
};

std::vector<std::string> split(const std::string& line) {
  std::vector<std::string> fields;
  std::stringstream input(line);
  std::string field;
  while (std::getline(input, field, ',')) fields.push_back(field);
  return fields;
}

std::vector<Metric> read_metrics(const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path);
  std::string line;
  std::getline(input, line);
  std::vector<Metric> result;
  while (std::getline(input, line)) {
    const auto f = split(line);
    if (f.size() < 20) continue;
    result.push_back({f[0], std::stod(f[1]), std::stod(f[2]),
                      std::stod(f[4]), std::stod(f[5]), std::stod(f[6]),
                      std::stod(f[12]), std::stod(f[19])});
  }
  return result;
}

void style() {
  gStyle->SetOptStat(0);
  gStyle->SetTextFont(42);
  gStyle->SetLabelFont(42, "XYZ");
  gStyle->SetTitleFont(42, "XYZ");
  gStyle->SetTitleSize(0.05, "XYZ");
  gStyle->SetLabelSize(0.043, "XYZ");
  gStyle->SetPadLeftMargin(0.14);
  gStyle->SetPadBottomMargin(0.13);
  gStyle->SetPadTopMargin(0.07);
  gStyle->SetPadRightMargin(0.05);
  gStyle->SetLegendBorderSize(0);
}

TGraphErrors* make_graph(const std::vector<Metric>& rows,
                         const std::string& type, int field, int color,
                         int marker) {
  std::vector<Metric> selected;
  for (const auto& row : rows) if (row.type == type) selected.push_back(row);
  std::sort(selected.begin(), selected.end(),
            [](const auto& a, const auto& b) { return a.mass < b.mass; });
  auto* graph = new TGraphErrors(static_cast<int>(selected.size()));
  for (size_t i = 0; i < selected.size(); ++i) {
    double value = 0.0, error = 0.0;
    if (field == 0) value = selected[i].auc;
    else if (field == 1) { value = selected[i].improvement; error = selected[i].improvement_error; }
    else value = 100.0 * selected[i].coupling_improvement;
    graph->SetPoint(static_cast<int>(i), selected[i].mass, value);
    graph->SetPointError(static_cast<int>(i), 0.0, error);
  }
  graph->SetLineColor(color);
  graph->SetMarkerColor(color);
  graph->SetLineWidth(3);
  graph->SetMarkerStyle(marker);
  graph->SetMarkerSize(1.0);
  return graph;
}

void save_ml_summary(const std::vector<Metric>& rows,
                     const std::string& output_prefix) {
  TCanvas canvas("ml_summary", "ml_summary", 900, 720);
  canvas.SetLogx();
  auto* vector = make_graph(rows, "vector", 1, TColor::GetColor("#198754"), 20);
  auto* scalar = make_graph(rows, "scalar", 1, TColor::GetColor("#6F42C1"), 21);
  TMultiGraph multigraph;
  multigraph.Add(vector, "LP");
  multigraph.Add(scalar, "LP");
  multigraph.Draw("A");
  multigraph.GetXaxis()->SetTitle("Boson mass m_{#phi} [GeV]");
  multigraph.GetYaxis()->SetTitle("Z_{ML}/Z_{Table I}");
  multigraph.GetXaxis()->SetLimits(0.007, 14.0);
  multigraph.SetMinimum(0.95);
  multigraph.SetMaximum(1.36);
  TLine line(0.007, 1.0, 14.0, 1.0);
  line.SetLineStyle(2);
  line.SetLineColor(kGray + 2);
  line.Draw();
  TLegend legend(0.18, 0.70, 0.54, 0.88);
  legend.AddEntry(vector, "Vector signal", "lp");
  legend.AddEntry(scalar, "Scalar signal", "lp");
  legend.AddEntry(&line, "No improvement", "l");
  legend.Draw();
  TLatex label;
  label.SetNDC();
  label.SetTextSize(0.034);
  label.DrawLatex(0.18, 0.90, "Our parton-level proof of concept");
  canvas.SaveAs((output_prefix + ".png").c_str());
  canvas.SaveAs((output_prefix + ".pdf").c_str());
}

void save_roc_summary(const std::vector<Metric>& rows,
                      const std::string& output_prefix) {
  TCanvas canvas("auc_summary", "auc_summary", 900, 720);
  canvas.SetLogx();
  auto* vector = make_graph(rows, "vector", 0, TColor::GetColor("#198754"), 20);
  auto* scalar = make_graph(rows, "scalar", 0, TColor::GetColor("#6F42C1"), 21);
  TMultiGraph multigraph;
  multigraph.Add(vector, "LP");
  multigraph.Add(scalar, "LP");
  multigraph.Draw("A");
  multigraph.GetXaxis()->SetTitle("Boson mass m_{#phi} [GeV]");
  multigraph.GetYaxis()->SetTitle("Weighted test ROC AUC");
  multigraph.GetXaxis()->SetLimits(0.007, 14.0);
  multigraph.SetMinimum(0.45);
  multigraph.SetMaximum(0.88);
  TLine line(0.007, 0.5, 14.0, 0.5);
  line.SetLineStyle(2);
  line.SetLineColor(kGray + 2);
  line.Draw();
  TLegend legend(0.18, 0.72, 0.49, 0.88);
  legend.AddEntry(vector, "Vector signal", "lp");
  legend.AddEntry(scalar, "Scalar signal", "lp");
  legend.Draw();
  canvas.SaveAs((output_prefix + ".png").c_str());
  canvas.SaveAs((output_prefix + ".pdf").c_str());
}

void save_score_distribution(const std::string& scores_path,
                             const std::string& output_prefix) {
  std::ifstream input(scores_path);
  if (!input) throw std::runtime_error("cannot open " + scores_path);
  TH1D signal("signal", "", 40, -1.0, 1.0);
  TH1D background("background", "", 40, -1.0, 1.0);
  signal.Sumw2(); background.Sumw2();
  std::string line;
  std::getline(input, line);
  while (std::getline(input, line)) {
    auto f = split(line);
    if (f.size() < 3) continue;
    const double score = std::stod(f[1]);
    const double weight = std::stod(f[2]);
    if (f[0] == "signal") signal.Fill(score, weight);
    else background.Fill(score, weight);
  }
  if (signal.Integral() > 0.0) signal.Scale(1.0 / signal.Integral(), "width");
  if (background.Integral() > 0.0) background.Scale(1.0 / background.Integral(), "width");
  signal.SetLineColor(TColor::GetColor("#198754"));
  signal.SetLineWidth(3);
  background.SetLineColor(kBlack);
  background.SetLineWidth(3);
  background.SetLineStyle(2);
  signal.SetTitle(";BDTG score;Normalized weighted density");
  signal.SetMaximum(1.25 * std::max(signal.GetMaximum(), background.GetMaximum()));
  TCanvas canvas("score", "score", 900, 720);
  signal.Draw("hist");
  background.Draw("hist same");
  TLegend legend(0.18, 0.75, 0.52, 0.88);
  legend.AddEntry(&signal, "10 GeV vector signal", "l");
  legend.AddEntry(&background, "Photon background", "l");
  legend.Draw();
  canvas.SaveAs((output_prefix + ".png").c_str());
  canvas.SaveAs((output_prefix + ".pdf").c_str());
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 4) return 2;
  style();
  const auto rows = read_metrics(argv[1]);
  save_ml_summary(rows, std::string(argv[2]) + "/ml_significance_improvement");
  save_roc_summary(rows, std::string(argv[2]) + "/weighted_auc");
  save_score_distribution(argv[3], std::string(argv[2]) + "/score_vector_10GeV");
  return 0;
}
