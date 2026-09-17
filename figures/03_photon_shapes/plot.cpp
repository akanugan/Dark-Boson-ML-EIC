#include <TMVA/Reader.h>

#include <TCanvas.h>
#include <TColor.h>
#include <TFile.h>
#include <TGraph.h>
#include <TH1D.h>
#include <TH2D.h>
#include <TLatex.h>
#include <TLegend.h>
#include <TLine.h>
#include <TMarker.h>
#include <TParameter.h>
#include <TStyle.h>
#include <TTree.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace fs = std::filesystem;

namespace {

constexpr int kBlue = 600;

struct Event {
  double log_q2 = 0.0;
  double log_t = 0.0;
  double pt = 0.0;
  double eta = 0.0;
  double energy = 0.0;
  double weight = 0.0;
};

struct RocPoint {
  double background_efficiency = 0.0;
  double signal_efficiency = 0.0;
  double threshold = std::numeric_limits<double>::infinity();
};

struct RocResult {
  std::vector<RocPoint> points;
  double auc = 0.0;
};

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

std::vector<std::map<std::string, std::string>> read_csv(
    const fs::path& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path.string());
  std::string line;
  if (!std::getline(input, line)) return {};
  const auto header = split_csv(line);
  std::vector<std::map<std::string, std::string>> rows;
  while (std::getline(input, line)) {
    if (line.empty()) continue;
    const auto values = split_csv(line);
    if (values.size() != header.size() || values == header) continue;
    std::map<std::string, std::string> row;
    for (std::size_t i = 0; i < header.size(); ++i) row[header[i]] = values[i];
    rows.push_back(std::move(row));
  }
  return rows;
}

double number(const std::map<std::string, std::string>& row,
              const std::string& name) {
  const auto found = row.find(name);
  if (found == row.end()) throw std::runtime_error("missing column " + name);
  return std::stod(found->second);
}

std::vector<Event> load_events(const fs::path& path, bool photon) {
  TFile file(path.c_str(), "READ");
  if (file.IsZombie()) throw std::runtime_error("cannot open " + path.string());
  auto* tree = dynamic_cast<TTree*>(file.Get("events"));
  if (!tree) throw std::runtime_error("missing events tree in " + path.string());
  auto* normalization = dynamic_cast<TParameter<double>*>(
      file.Get("pb_per_foam_weight"));
  if (!normalization) {
    throw std::runtime_error("missing pb_per_foam_weight in " + path.string());
  }

  double foam_weight = 0.0;
  double miss_probability = 1.0;
  double q2 = 0.0;
  double t = 0.0;
  double pt = 0.0;
  double eta = 0.0;
  double energy = 0.0;
  Bool_t pass_paper_cut = true;
  tree->SetBranchAddress("foam_weight", &foam_weight);
  tree->SetBranchAddress("Qe2", &q2);
  tree->SetBranchAddress("QA2", &t);  // Historical branch name; displayed as t.
  tree->SetBranchAddress("electron_pt", &pt);
  tree->SetBranchAddress("electron_eta", &eta);
  tree->SetBranchAddress("electron_energy", &energy);
  if (tree->GetBranch("pass_paper_cut")) {
    tree->SetBranchAddress("pass_paper_cut", &pass_paper_cut);
  }
  if (photon) {
    if (!tree->GetBranch("photon_miss_probability")) {
      throw std::runtime_error("missing photon miss probability in " +
                               path.string());
    }
    tree->SetBranchAddress("photon_miss_probability", &miss_probability);
  }

  std::vector<Event> result;
  result.reserve(static_cast<std::size_t>(tree->GetEntries()));
  const double pb_per_weight = normalization->GetVal();
  for (Long64_t index = 0; index < tree->GetEntries(); ++index) {
    tree->GetEntry(index);
    if (!pass_paper_cut) continue;
    Event event;
    event.log_q2 = std::log10(std::max(q2, 1.0e-30));
    event.log_t = std::log10(std::max(t, 1.0e-30));
    event.pt = pt;
    event.eta = eta;
    event.energy = energy;
    event.weight = foam_weight * pb_per_weight *
                   (photon ? miss_probability : 1.0);
    if (event.weight < 0.0 || !std::isfinite(event.weight) ||
        !std::isfinite(event.log_q2) || !std::isfinite(event.log_t)) {
      throw std::runtime_error("invalid event in " + path.string());
    }
    result.push_back(event);
  }
  return result;
}

double sum_weights(const std::vector<Event>& events) {
  double total = 0.0;
  for (const auto& event : events) total += event.weight;
  return total;
}

class BdtScorer {
 public:
  BdtScorer(const fs::path& weights_path, bool with_t)
      : with_t_(with_t), reader_("!Color:!Silent") {
    reader_.AddVariable("log10(Qe2)", &log_q2_);
    if (with_t_) reader_.AddVariable("log10(QA2)", &log_t_);
    reader_.AddVariable("electron_pt", &pt_);
    reader_.AddVariable("electron_eta", &eta_);
    reader_.AddVariable("electron_energy", &energy_);
    reader_.BookMVA("BDTG", weights_path.c_str());
  }

  double score(const Event& event) {
    log_q2_ = static_cast<float>(event.log_q2);
    log_t_ = static_cast<float>(event.log_t);
    pt_ = static_cast<float>(event.pt);
    eta_ = static_cast<float>(event.eta);
    energy_ = static_cast<float>(event.energy);
    return reader_.EvaluateMVA("BDTG");
  }

 private:
  bool with_t_ = false;
  float log_q2_ = 0.0F;
  float log_t_ = 0.0F;
  float pt_ = 0.0F;
  float eta_ = 0.0F;
  float energy_ = 0.0F;
  TMVA::Reader reader_;
};

RocResult weighted_roc(const std::vector<Event>& signal,
                       const std::vector<Event>& background,
                       BdtScorer& scorer) {
  struct Scored {
    double score;
    double weight;
    bool signal;
  };
  std::vector<Scored> events;
  events.reserve(signal.size() + background.size());
  for (const auto& event : signal) {
    events.push_back({scorer.score(event), event.weight, true});
  }
  for (const auto& event : background) {
    events.push_back({scorer.score(event), event.weight, false});
  }
  std::sort(events.begin(), events.end(), [](const Scored& left,
                                              const Scored& right) {
    return left.score > right.score;
  });

  const double signal_total = sum_weights(signal);
  const double background_total = sum_weights(background);
  if (!(signal_total > 0.0 && background_total > 0.0)) {
    throw std::runtime_error("zero total weight in ROC sample");
  }
  RocResult result;
  result.points.push_back({0.0, 0.0, std::numeric_limits<double>::infinity()});
  double signal_pass = 0.0;
  double background_pass = 0.0;
  std::size_t index = 0;
  while (index < events.size()) {
    const double threshold = events[index].score;
    std::size_t next = index;
    while (next < events.size() && events[next].score == threshold) {
      if (events[next].signal) signal_pass += events[next].weight;
      else background_pass += events[next].weight;
      ++next;
    }
    result.points.push_back({background_pass / background_total,
                             signal_pass / signal_total, threshold});
    index = next;
  }
  for (std::size_t i = 1; i < result.points.size(); ++i) {
    const auto& left = result.points[i - 1];
    const auto& right = result.points[i];
    result.auc += (right.background_efficiency - left.background_efficiency) *
                  0.5 * (left.signal_efficiency + right.signal_efficiency);
  }
  return result;
}

std::unique_ptr<TGraph> roc_graph(const RocResult& roc) {
  const std::size_t target = 1400;
  const std::size_t stride = std::max<std::size_t>(1, roc.points.size() / target);
  std::vector<double> x;
  std::vector<double> y;
  x.reserve(target + 2);
  y.reserve(target + 2);
  for (std::size_t i = 0; i < roc.points.size(); i += stride) {
    x.push_back(roc.points[i].background_efficiency);
    y.push_back(roc.points[i].signal_efficiency);
  }
  if (x.empty() || x.back() != roc.points.back().background_efficiency) {
    x.push_back(roc.points.back().background_efficiency);
    y.push_back(roc.points.back().signal_efficiency);
  }
  return std::make_unique<TGraph>(static_cast<int>(x.size()), x.data(), y.data());
}

void configure_style() {
  gStyle->SetOptStat(0);
  gStyle->SetTitleFont(42, "XYZ");
  gStyle->SetLabelFont(42, "XYZ");
  gStyle->SetTextFont(42);
  gStyle->SetTitleSize(0.047, "XYZ");
  gStyle->SetLabelSize(0.040, "XYZ");
  gStyle->SetTitleOffset(1.15, "X");
  gStyle->SetTitleOffset(1.35, "Y");
  gStyle->SetLegendFont(42);
  gStyle->SetPalette(kViridis);
  gStyle->SetNumberContours(100);
}

fs::path sealed_path(const fs::path& root, const std::string& type,
                     const std::string& tag) {
  return root / "data/ml/sealed/root" /
         (type + "_m" + tag + "_sealed.root");
}

void write_density_csv(
    const fs::path& path,
    const std::vector<std::tuple<std::string, double, TH2D*>>& hists) {
  std::ofstream output(path);
  output << "class,mass_GeV,pt_low_GeV,pt_high_GeV,log10_t_low,log10_t_high,weighted_probability_percent\n";
  output << std::setprecision(12);
  for (const auto& [label, mass, histogram] : hists) {
    for (int x = 1; x <= histogram->GetNbinsX(); ++x) {
      for (int y = 1; y <= histogram->GetNbinsY(); ++y) {
        output << label << ',' << mass << ','
               << histogram->GetXaxis()->GetBinLowEdge(x) << ','
               << histogram->GetXaxis()->GetBinUpEdge(x) << ','
               << histogram->GetYaxis()->GetBinLowEdge(y) << ','
               << histogram->GetYaxis()->GetBinUpEdge(y) << ','
               << histogram->GetBinContent(x, y) << '\n';
      }
    }
  }
}

void make_density_figure(const fs::path& root, const fs::path& out) {
  struct RowConfig {
    std::string tag;
    double mass;
    double pt_min;
    double pt_max;
    double log_t_min;
    double log_t_max;
  };
  const std::vector<RowConfig> rows{{"1p000", 1.0, 1.1, 7.5, -6.0, -1.5},
                                    {"10p000", 10.0, 1.3, 9.5, -4.8, -1.0}};
  const std::vector<std::pair<std::string, std::string>> classes{
      {"photon", "Photon proxy"}, {"vector", "Vector signal"},
      {"scalar", "Scalar signal"}};

  std::vector<std::unique_ptr<TH2D>> owned;
  std::vector<std::tuple<std::string, double, TH2D*>> histograms;
  std::map<std::pair<std::string, double>, double> totals;
  std::vector<double> row_maximum(rows.size(), 0.0);
  for (std::size_t row = 0; row < rows.size(); ++row) {
    for (std::size_t column = 0; column < classes.size(); ++column) {
      const auto& [type, display] = classes[column];
      const auto events = load_events(sealed_path(root, type, rows[row].tag),
                                      type == "photon");
      const std::string name = "density_" + type + '_' + rows[row].tag;
      auto histogram = std::make_unique<TH2D>(
          name.c_str(), "", 36, rows[row].pt_min, rows[row].pt_max,
          36, rows[row].log_t_min, rows[row].log_t_max);
      histogram->SetDirectory(nullptr);
      const double total = sum_weights(events);
      totals[{display, rows[row].mass}] = total;
      for (const auto& event : events) {
        histogram->Fill(event.pt, event.log_t, event.weight);
      }
      if (!(total > 0.0)) throw std::runtime_error("empty density sample");
      histogram->Scale(100.0 / total);
      row_maximum[row] = std::max(row_maximum[row], histogram->GetMaximum());
      histograms.push_back({display, rows[row].mass, histogram.get()});
      owned.push_back(std::move(histogram));
    }
  }

  TCanvas canvas("density_canvas", "", 1800, 1030);
  canvas.Divide(3, 2, 0.002, 0.002);
  TLatex text;
  text.SetTextFont(42);
  for (std::size_t row = 0; row < rows.size(); ++row) {
    for (std::size_t column = 0; column < classes.size(); ++column) {
      const int pad_index = static_cast<int>(row * classes.size() + column + 1);
      canvas.cd(pad_index);
      gPad->SetLeftMargin(column == 0 ? 0.16 : 0.12);
      gPad->SetRightMargin(0.15);
      gPad->SetBottomMargin(0.15);
      gPad->SetTopMargin(0.10);
      gPad->SetLogz();
      auto* histogram = std::get<2>(histograms[pad_index - 1]);
      histogram->SetMinimum(2.0e-4);
      histogram->SetMaximum(row_maximum[row] * 1.05);
      histogram->GetXaxis()->SetTitle("p_{T,e} [GeV]");
      histogram->GetYaxis()->SetTitle("log_{10}(t/GeV^{2})");
      histogram->GetZaxis()->SetTitle("Weighted events [%/bin]");
      histogram->GetZaxis()->SetTitleSize(0.037);
      histogram->GetZaxis()->SetLabelSize(0.032);
      histogram->GetZaxis()->SetTitleOffset(1.2);
      histogram->Draw("COLZ");
      text.SetTextSize(0.050);
      text.DrawLatexNDC(0.18, 0.93, classes[column].second.c_str());
      text.SetTextSize(0.043);
      const std::string mass = "m_{#phi} = " +
          std::string(row == 0 ? "1" : "10") + " GeV";
      text.DrawLatexNDC(0.18, 0.865, mass.c_str());
    }
  }
  canvas.SaveAs((out / "t_pt_density.png").c_str());
  canvas.SaveAs((out / "t_pt_density.pdf").c_str());
  write_density_csv(out / "t_pt_density.csv", histograms);
}

void style_histogram(TH1D& histogram, int color, int style) {
  histogram.SetLineColor(color);
  histogram.SetLineWidth(3);
  histogram.SetLineStyle(style);
}

void make_photon_overlay(const fs::path& root, const fs::path& out) {
  const auto rows = read_csv(fs::path(__FILE__).parent_path() / "data/distributions.csv");
  struct Values { std::vector<double> edge, published, ours; };
  std::map<std::string, Values> values;
  for (const auto& row : rows) {
    const auto observable = row.at("observable");
    values[observable].edge.push_back(number(row, "left_edge"));
    values[observable].published.push_back(number(row, "published_probability"));
    values[observable].ours.push_back(number(row, "our_model_probability"));
  }

  TFile inclusive_file((root / "data/ml/validation/photon_inclusive.root").c_str(),
                       "READ");
  auto* inclusive_tree = dynamic_cast<TTree*>(inclusive_file.Get("events"));
  if (!inclusive_tree) throw std::runtime_error("missing inclusive photon tree");
  double inclusive_weight = 0.0;
  double inclusive_pt = 0.0;
  double inclusive_eta = 0.0;
  inclusive_tree->SetBranchAddress("foam_weight", &inclusive_weight);
  inclusive_tree->SetBranchAddress("electron_pt", &inclusive_pt);
  inclusive_tree->SetBranchAddress("electron_eta", &inclusive_eta);
  double total_weight = 0.0;
  double pt_inside = 0.0;
  double eta_inside = 0.0;
  const double pt_low = values.at("log10_electron_pt").edge.front();
  const double pt_high = values.at("log10_electron_pt").edge.back() + 0.5;
  const double eta_low = values.at("electron_eta").edge.front();
  const double eta_high = values.at("electron_eta").edge.back() + 1.0;
  for (Long64_t index = 0; index < inclusive_tree->GetEntries(); ++index) {
    inclusive_tree->GetEntry(index);
    total_weight += inclusive_weight;
    const double log_pt = std::log10(std::max(inclusive_pt, 1.0e-99));
    if (log_pt >= pt_low && log_pt < pt_high) pt_inside += inclusive_weight;
    if (inclusive_eta >= eta_low && inclusive_eta < eta_high) {
      eta_inside += inclusive_weight;
    }
  }
  const std::map<std::string, double> outside_fraction{
      {"log10_electron_pt", 1.0 - pt_inside / total_weight},
      {"electron_eta", 1.0 - eta_inside / total_weight}};

  TCanvas canvas("photon_overlay_canvas", "", 1500, 650);
  canvas.Divide(2, 1, 0.01, 0.01);
  std::vector<std::unique_ptr<TH1D>> owned_histograms;
  std::vector<std::unique_ptr<TLegend>> owned_legends;
  const std::vector<std::tuple<std::string, std::string, double>> configs{
      {"log10_electron_pt", "log_{10}(p_{T,e}/GeV)", 0.714869},
      {"electron_eta", "#eta_{e}", 0.409142}};
  TLatex text;
  text.SetTextFont(42);
  for (std::size_t panel = 0; panel < configs.size(); ++panel) {
    canvas.cd(static_cast<int>(panel + 1));
    gPad->SetLeftMargin(0.14);
    gPad->SetRightMargin(0.04);
    gPad->SetBottomMargin(0.15);
    gPad->SetTopMargin(0.08);
    gPad->SetLogy();
    const auto& [observable, x_title, tv] = configs[panel];
    const auto& entry = values.at(observable);
    const double width = panel == 0 ? 0.5 : 1.0;
    std::vector<double> edges = entry.edge;
    edges.push_back(edges.back() + width);
    auto published = std::make_unique<TH1D>(
        ("published_" + observable).c_str(), "",
        static_cast<int>(entry.edge.size()), edges.data());
    auto ours = std::make_unique<TH1D>(
        ("ours_" + observable).c_str(), "",
        static_cast<int>(entry.edge.size()), edges.data());
    published->SetDirectory(nullptr);
    ours->SetDirectory(nullptr);
    for (std::size_t i = 0; i < entry.edge.size(); ++i) {
      published->SetBinContent(static_cast<int>(i + 1), entry.published[i]);
      ours->SetBinContent(static_cast<int>(i + 1), entry.ours[i]);
    }
    published->Scale(1.0 / published->Integral());
    ours->Scale(1.0 / ours->Integral());
    style_histogram(*published, 1, 1);
    style_histogram(*ours, kBlue, 2);
    published->SetMinimum(panel == 0 ? 5.0e-13 : 5.0e-9);
    published->SetMaximum(2.0);
    published->GetXaxis()->SetTitle(x_title.c_str());
    published->GetYaxis()->SetTitle("Normalized probability per bin");
    published->Draw("HIST");
    ours->Draw("HIST SAME");
    auto legend = std::make_unique<TLegend>(0.53, 0.72, 0.92, 0.90);
    legend->SetBorderSize(0);
    legend->SetFillStyle(0);
    legend->SetTextSize(0.040);
    legend->AddEntry(published.get(), "Public ancillary", "l");
    legend->AddEntry(ours.get(), "Our photon proxy", "l");
    legend->Draw();
    text.SetTextSize(0.036);
    text.DrawLatexNDC(0.18, 0.30, "Inclusive shape diagnostic");
    std::ostringstream label;
    label << "TV distance = " << std::fixed << std::setprecision(3) << tv;
    text.DrawLatexNDC(0.18, 0.235, label.str().c_str());
    std::ostringstream outside_label;
    outside_label << "Proxy outside range = " << std::fixed
                  << std::setprecision(1) << 100.0 * outside_fraction.at(observable)
                  << "%";
    text.DrawLatexNDC(0.18, 0.17, outside_label.str().c_str());
    owned_histograms.push_back(std::move(published));
    owned_histograms.push_back(std::move(ours));
    owned_legends.push_back(std::move(legend));
  }
  canvas.SaveAs((out / "photon_shape_overlay.png").c_str());
  canvas.SaveAs((out / "photon_shape_overlay.pdf").c_str());
  std::ofstream summary(out / "photon_shape_overlay_summary.csv");
  summary << "observable,range_conditioned_total_variation,proxy_outside_public_range_fraction\n";
  summary << std::setprecision(12)
          << "log10_electron_pt,0.714869,"
          << outside_fraction.at("log10_electron_pt") << '\n'
          << "electron_eta,0.409142,"
          << outside_fraction.at("electron_eta") << '\n';
}

std::string selected_weights(const std::vector<std::map<std::string, std::string>>& rows,
                             const std::string& signal, const std::string& feature) {
  for (const auto& row : rows) {
    if (row.at("signal_type") == signal &&
        std::abs(number(row, "mass_GeV") - 10.0) < 1.0e-8 &&
        row.at("feature_set") == feature) {
      return row.at("weights_path");
    }
  }
  throw std::runtime_error("missing selected model for " + signal + " " + feature);
}

std::pair<double, double> selected_box_point(
    const std::vector<std::map<std::string, std::string>>& rows,
    const std::string& signal, const std::string& feature) {
  for (const auto& row : rows) {
    if (row.at("signal_type") == signal &&
        std::abs(number(row, "mass_GeV") - 10.0) < 1.0e-8 &&
        row.at("feature_set") == feature) {
      return {number(row, "box_photon_efficiency"),
              number(row, "box_signal_efficiency")};
    }
  }
  throw std::runtime_error("missing sealed metric for " + signal + " " + feature);
}

void write_roc_csv(const fs::path& path,
                   const std::map<std::pair<std::string, std::string>, RocResult>& rocs,
                   const std::map<std::pair<std::string, std::string>,
                                  std::pair<double, double>>& boxes) {
  std::ofstream output(path);
  output << "signal_type,feature_set,method,point_index,photon_efficiency,signal_efficiency,threshold,auc\n";
  output << std::setprecision(12);
  for (const auto& [key, roc] : rocs) {
    for (std::size_t i = 0; i < roc.points.size(); ++i) {
      output << key.first << ',' << (key.second == "electron" ? "observables" : "observables+t")
             << ",BDT," << i << ',' << roc.points[i].background_efficiency
             << ',' << roc.points[i].signal_efficiency << ','
             << roc.points[i].threshold << ',' << roc.auc << '\n';
    }
    const auto point = boxes.at(key);
    output << key.first << ',' << (key.second == "electron" ? "observables" : "observables+t")
           << ",optimized_cuts,0," << point.first << ',' << point.second
           << ",NA,NA\n";
  }
}

void make_roc_figure(const fs::path& root, const fs::path& out) {
  const auto selected = read_csv(root / "fair_study/rigorous/development_frozen/selected_models.csv");
  const auto final_metrics = read_csv(root / "fair_study/rigorous/final/rigorous_final_metrics.csv");
  const auto photon = load_events(sealed_path(root, "photon", "10p000"), true);
  std::map<std::pair<std::string, std::string>, RocResult> rocs;
  std::map<std::pair<std::string, std::string>, std::pair<double, double>> boxes;
  for (const std::string& signal_type : {"vector", "scalar"}) {
    const auto signal = load_events(sealed_path(root, signal_type, "10p000"), false);
    for (const std::string& feature : {"electron", "electron_qa2"}) {
      BdtScorer scorer(selected_weights(selected, signal_type, feature),
                       feature == "electron_qa2");
      rocs[{signal_type, feature}] = weighted_roc(signal, photon, scorer);
      boxes[{signal_type, feature}] = selected_box_point(final_metrics, signal_type, feature);
      std::cout << signal_type << ' ' << feature << " sealed AUC="
                << std::setprecision(8) << rocs[{signal_type, feature}].auc << '\n';
    }
  }

  TCanvas canvas("roc_canvas", "", 1500, 650);
  canvas.Divide(2, 1, 0.01, 0.01);
  std::vector<std::unique_ptr<TH1D>> owned_frames;
  std::vector<std::unique_ptr<TGraph>> owned_graphs;
  std::vector<std::unique_ptr<TMarker>> owned_markers;
  std::vector<std::unique_ptr<TLegend>> owned_legends;
  TLatex text;
  text.SetTextFont(42);
  for (std::size_t panel = 0; panel < 2; ++panel) {
    const std::string signal_type = panel == 0 ? "vector" : "scalar";
    canvas.cd(static_cast<int>(panel + 1));
    gPad->SetLeftMargin(0.14);
    gPad->SetRightMargin(0.04);
    gPad->SetBottomMargin(0.15);
    gPad->SetTopMargin(0.08);
    gPad->SetLogx();

    auto frame = std::make_unique<TH1D>(
        ("roc_frame_" + signal_type).c_str(), "", 100, 1.0e-3, 1.0);
    frame->SetDirectory(nullptr);
    frame->SetMinimum(0.0);
    frame->SetMaximum(1.03);
    frame->GetXaxis()->SetTitle("Photon-proxy efficiency #epsilon_{#gamma}");
    frame->GetYaxis()->SetTitle("Signal efficiency #epsilon_{S}");
    frame->Draw("AXIS");
    std::vector<double> random_x(120), random_y(120);
    for (std::size_t i = 0; i < random_x.size(); ++i) {
      const double exponent = -3.0 + 3.0 * i / (random_x.size() - 1.0);
      random_x[i] = std::pow(10.0, exponent);
      random_y[i] = random_x[i];
    }
    auto random_classifier = std::make_unique<TGraph>(
        static_cast<int>(random_x.size()), random_x.data(), random_y.data());
    random_classifier->SetLineColor(kGray + 1);
    random_classifier->SetLineStyle(3);
    random_classifier->Draw("L SAME");

    auto obs = roc_graph(rocs.at({signal_type, "electron"}));
    auto with_t = roc_graph(rocs.at({signal_type, "electron_qa2"}));
    obs->SetLineColor(1);
    obs->SetLineWidth(3);
    with_t->SetLineColor(kBlue);
    with_t->SetLineWidth(3);
    obs->Draw("L SAME");
    with_t->Draw("L SAME");

    const auto box_obs = boxes.at({signal_type, "electron"});
    const auto box_t = boxes.at({signal_type, "electron_qa2"});
    auto marker_obs = std::make_unique<TMarker>(box_obs.first, box_obs.second, 20);
    auto marker_t = std::make_unique<TMarker>(box_t.first, box_t.second, 20);
    marker_obs->SetMarkerColor(1);
    marker_t->SetMarkerColor(kBlue);
    marker_obs->SetMarkerSize(1.5);
    marker_t->SetMarkerSize(1.5);
    marker_obs->Draw();
    marker_t->Draw();

    std::ostringstream obs_label;
    obs_label << "BDT: observables (AUC " << std::fixed << std::setprecision(3)
              << rocs.at({signal_type, "electron"}).auc << ')';
    std::ostringstream t_label;
    t_label << "BDT: observables + exact t (AUC " << std::fixed
            << std::setprecision(3)
            << rocs.at({signal_type, "electron_qa2"}).auc << ')';
    auto legend = std::make_unique<TLegend>(0.18, 0.20, 0.66, 0.43);
    legend->SetBorderSize(0);
    legend->SetFillStyle(0);
    legend->SetTextSize(0.034);
    legend->AddEntry(obs.get(), obs_label.str().c_str(), "l");
    legend->AddEntry(with_t.get(), t_label.str().c_str(), "l");
    legend->AddEntry(marker_obs.get(), "Optimized cuts: observables", "p");
    legend->AddEntry(marker_t.get(), "Optimized cuts: observables + exact t", "p");
    legend->Draw();

    text.SetTextSize(0.048);
    text.DrawLatexNDC(0.18, 0.90,
        panel == 0 ? "Vector signal, m_{#phi}=10 GeV" :
                     "Scalar signal, m_{#phi}=10 GeV");
    text.SetTextSize(0.034);
    text.DrawLatexNDC(0.18, 0.84, "Sealed post-Table-I sample");
    owned_frames.push_back(std::move(frame));
    owned_graphs.push_back(std::move(random_classifier));
    owned_graphs.push_back(std::move(obs));
    owned_graphs.push_back(std::move(with_t));
    owned_markers.push_back(std::move(marker_obs));
    owned_markers.push_back(std::move(marker_t));
    owned_legends.push_back(std::move(legend));
  }
  canvas.SaveAs((out / "roc_t_comparison.png").c_str());
  canvas.SaveAs((out / "roc_t_comparison.pdf").c_str());
  write_roc_csv(out / "roc_t_comparison.csv", rocs, boxes);
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 3) {
      throw std::runtime_error("usage: plot PROJECT_ROOT OUTPUT_DIR");
    }
    const fs::path root = fs::absolute(argv[1]);
    const fs::path output = fs::absolute(argv[2]);
    fs::create_directories(output);
    configure_style();

    make_photon_overlay(root, output);

    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
