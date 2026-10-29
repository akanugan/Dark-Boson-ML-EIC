#include <TCanvas.h>
#include <TColor.h>
#include <TGraph.h>
#include <TGraphErrors.h>
#include <TH1D.h>
#include <TLatex.h>
#include <TLegend.h>
#include <TStyle.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

std::vector<std::string> split_csv(const std::string& line) {
  std::vector<std::string> fields;
  std::string field;
  bool in_quotes = false;
  for (std::size_t i = 0; i < line.size(); ++i) {
    const char value = line[i];
    if (value == '"') {
      if (in_quotes && i + 1 < line.size() && line[i + 1] == '"') {
        field.push_back('"');
        ++i;
      } else {
        in_quotes = !in_quotes;
      }
    } else if (value == ',' && !in_quotes) {
      fields.push_back(field);
      field.clear();
    } else {
      field.push_back(value);
    }
  }
  fields.push_back(field);
  return fields;
}

struct Summary {
  std::vector<double> value;
  double mean = 0.0;
  double sample_sd = 0.0;
};

std::map<std::pair<std::string, std::string>, Summary> read_importance(
    const fs::path& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path.string());
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty CSV");
  const auto header = split_csv(line);
  std::map<std::string, std::size_t> column;
  for (std::size_t i = 0; i < header.size(); ++i) column[header[i]] = i;
  std::map<std::pair<std::string, std::string>, Summary> result;
  while (std::getline(input, line)) {
    if (line.empty()) continue;
    const auto fields = split_csv(line);
    if (fields.size() != header.size()) {
      throw std::runtime_error("malformed CSV line: " + line);
    }
    result[{fields[column.at("signal_type")], fields[column.at("feature")]}]
        .value.push_back(std::stod(fields[column.at("importance")]));
  }
  for (auto& [key, summary] : result) {
    if (summary.value.size() != 10) {
      throw std::runtime_error("expected ten replicas for " + key.first +
                               " " + key.second);
    }
    summary.mean = std::accumulate(summary.value.begin(), summary.value.end(),
                                   0.0) / summary.value.size();
    double squared = 0.0;
    for (double value : summary.value) {
      squared += (value - summary.mean) * (value - summary.mean);
    }
    summary.sample_sd = std::sqrt(squared / (summary.value.size() - 1));
  }
  return result;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 3) {
      throw std::runtime_error("usage: plot_tmva_importance INPUT.csv OUTPUT_DIR");
    }
    const fs::path input = fs::absolute(argv[1]);
    const fs::path output = fs::absolute(argv[2]);
    fs::create_directories(output);
    const auto values = read_importance(input);
    const std::vector<std::string> features{"Q^2", "pT,e", "eta_e", "E_e", "t"};
    const std::vector<std::string> labels{"Q^{2}", "p_{T,e}", "#eta_{e}",
                                          "E_{e}", "t"};
    const int vector_color = TColor::GetColor("#1B8E5A");
    const int scalar_color = TColor::GetColor("#6F42C1");

    gStyle->SetOptStat(0);
    gStyle->SetTextFont(42);
    gStyle->SetLabelFont(42, "XYZ");
    gStyle->SetTitleFont(42, "XYZ");
    gStyle->SetLabelSize(0.045, "XYZ");
    gStyle->SetTitleSize(0.050, "XYZ");

    TCanvas canvas("importance_canvas", "", 1100, 720);
    canvas.SetLeftMargin(0.12);
    canvas.SetRightMargin(0.04);
    canvas.SetBottomMargin(0.15);
    canvas.SetTopMargin(0.10);
    canvas.SetGridy();

    TH1D frame("importance_frame", "", 5, 0.5, 5.5);
    frame.SetDirectory(nullptr);
    frame.SetMinimum(0.0);
    frame.SetMaximum(0.35);
    frame.GetYaxis()->SetTitle("TMVA BDT variable importance");
    frame.GetXaxis()->SetTitle("Input feature");
    frame.GetYaxis()->SetTitleOffset(1.05);
    for (int bin = 1; bin <= 5; ++bin) {
      frame.GetXaxis()->SetBinLabel(bin, labels[bin - 1].c_str());
    }
    frame.Draw("AXIS");

    TH1D vector_bar("vector_bar", "", 5, 0.5, 5.5);
    TH1D scalar_bar("scalar_bar", "", 5, 0.5, 5.5);
    vector_bar.SetDirectory(nullptr);
    scalar_bar.SetDirectory(nullptr);
    vector_bar.SetBarWidth(0.36);
    vector_bar.SetBarOffset(0.08);
    scalar_bar.SetBarWidth(0.36);
    scalar_bar.SetBarOffset(0.56);
    vector_bar.SetFillColorAlpha(vector_color, 0.35);
    scalar_bar.SetFillColorAlpha(scalar_color, 0.35);
    vector_bar.SetLineColor(vector_color);
    scalar_bar.SetLineColor(scalar_color);
    vector_bar.SetLineWidth(2);
    scalar_bar.SetLineWidth(2);

    std::vector<double> vector_x, scalar_x, vector_mean, scalar_mean;
    std::vector<double> vector_error, scalar_error, zero(5, 0.0);
    std::vector<double> vector_replica_x, scalar_replica_x;
    std::vector<double> vector_replica_y, scalar_replica_y;
    for (std::size_t i = 0; i < features.size(); ++i) {
      const auto& vector_summary = values.at({"vector", features[i]});
      const auto& scalar_summary = values.at({"scalar", features[i]});
      vector_bar.SetBinContent(static_cast<int>(i + 1), vector_summary.mean);
      scalar_bar.SetBinContent(static_cast<int>(i + 1), scalar_summary.mean);
      vector_x.push_back(i + 1.0 - 0.20);
      scalar_x.push_back(i + 1.0 + 0.20);
      vector_mean.push_back(vector_summary.mean);
      scalar_mean.push_back(scalar_summary.mean);
      vector_error.push_back(vector_summary.sample_sd);
      scalar_error.push_back(scalar_summary.sample_sd);
      for (std::size_t replica = 0; replica < 10; ++replica) {
        const double jitter = -0.075 + 0.15 * replica / 9.0;
        vector_replica_x.push_back(vector_x.back() + jitter);
        scalar_replica_x.push_back(scalar_x.back() + jitter);
        vector_replica_y.push_back(vector_summary.value[replica]);
        scalar_replica_y.push_back(scalar_summary.value[replica]);
      }
    }
    vector_bar.Draw("BAR SAME");
    scalar_bar.Draw("BAR SAME");

    TGraph vector_replicas(static_cast<int>(vector_replica_x.size()),
                           vector_replica_x.data(), vector_replica_y.data());
    TGraph scalar_replicas(static_cast<int>(scalar_replica_x.size()),
                           scalar_replica_x.data(), scalar_replica_y.data());
    vector_replicas.SetMarkerStyle(20);
    scalar_replicas.SetMarkerStyle(20);
    vector_replicas.SetMarkerSize(0.55);
    scalar_replicas.SetMarkerSize(0.55);
    vector_replicas.SetMarkerColorAlpha(vector_color, 0.55);
    scalar_replicas.SetMarkerColorAlpha(scalar_color, 0.55);
    vector_replicas.Draw("P SAME");
    scalar_replicas.Draw("P SAME");

    TGraphErrors vector_summary_graph(5, vector_x.data(), vector_mean.data(),
                                      zero.data(), vector_error.data());
    TGraphErrors scalar_summary_graph(5, scalar_x.data(), scalar_mean.data(),
                                      zero.data(), scalar_error.data());
    vector_summary_graph.SetMarkerStyle(20);
    scalar_summary_graph.SetMarkerStyle(20);
    vector_summary_graph.SetMarkerSize(1.2);
    scalar_summary_graph.SetMarkerSize(1.2);
    vector_summary_graph.SetMarkerColor(vector_color);
    scalar_summary_graph.SetMarkerColor(scalar_color);
    vector_summary_graph.SetLineColor(vector_color);
    scalar_summary_graph.SetLineColor(scalar_color);
    vector_summary_graph.SetLineWidth(2);
    scalar_summary_graph.SetLineWidth(2);
    vector_summary_graph.Draw("P E1 SAME");
    scalar_summary_graph.Draw("P E1 SAME");

    TLegend legend(0.15, 0.71, 0.43, 0.86);
    legend.SetBorderSize(0);
    legend.SetFillStyle(0);
    legend.SetTextSize(0.040);
    legend.AddEntry(&vector_summary_graph, "Vector signal", "pe");
    legend.AddEntry(&scalar_summary_graph, "Scalar signal", "pe");
    legend.Draw();

    TLatex text;
    text.SetTextFont(42);
    text.SetTextSize(0.036);
    text.DrawLatexNDC(0.62, 0.84, "10 GeV exact-t BDTs");
    text.SetTextSize(0.031);
    text.DrawLatexNDC(0.56, 0.78, "10 replicas; bars: mean #pm sample SD");

    canvas.SaveAs((output / "tmva_t_importance.png").c_str());
    canvas.SaveAs((output / "tmva_t_importance.pdf").c_str());

    std::ofstream summary(output / "tmva_t_importance_summary.csv");
    summary << "signal_type,feature,mean_importance,sample_sd,n\n";
    summary << std::setprecision(12);
    for (const std::string& signal : {"vector", "scalar"}) {
      for (const auto& feature : features) {
        const auto& item = values.at({signal, feature});
        summary << signal << ',' << (feature == "pT,e" ? "pT_e" : feature)
                << ',' << item.mean << ',' << item.sample_sd << ','
                << item.value.size() << '\n';
      }
    }
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
