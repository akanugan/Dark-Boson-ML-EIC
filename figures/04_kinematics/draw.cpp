// Draw the saved corrected-study bins with the original ROOT styling.
#include <TCanvas.h>
#include <TFile.h>
#include <TH2D.h>
#include <TLatex.h>
#include <TParameter.h>
#include <TROOT.h>
#include <TStyle.h>
#include <TTree.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

struct Panel {
  std::string type, display, tag;
  double mass, pt_min, pt_max, log_t_min, log_t_max;
  std::unique_ptr<TH2D> histogram;
};

int main(int argc, char** argv) {
  try {
    if (argc != 3) throw std::runtime_error("Usage: draw BINS_CSV OUTPUT_DIR");
    const fs::path csv = argv[1], media = argv[2];
    fs::create_directories(media);
    gROOT->SetBatch(true);
    gStyle->SetOptStat(0);
    gStyle->SetTitleFont(42, "XYZ"); gStyle->SetLabelFont(42, "XYZ");
    gStyle->SetTextFont(42); gStyle->SetPalette(kViridis);
    gStyle->SetNumberContours(100);
    std::vector<Panel> panels;
    for (const std::string tag : {"1p000", "10p000"}) {
      const bool low = tag == "1p000";
      for (const auto& type : {std::string("photon"), std::string("vector"), std::string("scalar")})
        panels.push_back({type, type == "photon" ? "Photon background" : type == "vector" ? "Vector signal" : "Scalar signal",
                          tag, low ? 1.0 : 10.0, low ? 1.1 : 1.3, low ? 7.5 : 9.5,
                          low ? -6.0 : -4.8, low ? -1.5 : -1.0, nullptr});
    }
    for (auto& panel : panels) {
      panel.histogram = std::make_unique<TH2D>(
          ("density_" + panel.type + "_" + panel.tag).c_str(), "", 36,
          panel.pt_min, panel.pt_max, 36, panel.log_t_min, panel.log_t_max);
      panel.histogram->SetDirectory(nullptr);
    }
    std::ifstream input(csv);
    if (!input) throw std::runtime_error("Cannot open binned data");
    std::string line;
    std::getline(input, line);
    std::vector<int> counts(6, 0);
    while (std::getline(input, line)) {
      std::stringstream stream(line);
      std::vector<std::string> fields;
      std::string item;
      while (std::getline(stream, item, ',')) fields.push_back(item);
      if (fields.size() != 7) throw std::runtime_error("Invalid CSV row");
      const double mass = std::stod(fields[1]);
      std::size_t index = 0;
      while (index < panels.size() && (panels[index].type != fields[0] || panels[index].mass != mass)) ++index;
      if (index == panels.size()) throw std::runtime_error("Unknown panel");
      const int cell = counts[index]++;
      if (cell >= 1296) throw std::runtime_error("Too many panel bins");
      panels[index].histogram->SetBinContent(cell / 36 + 1, cell % 36 + 1, std::stod(fields[6]));
    }
    for (const auto count : counts) if (count != 1296) throw std::runtime_error("Missing panel bins");
    TCanvas canvas("repaired_density", "", 2100, 1400);
    canvas.Divide(3, 2, 0.002, 0.002);
    TLatex text; text.SetTextFont(42);
    for (std::size_t row = 0; row < 2; ++row) {
      double maximum = 0;
      for (std::size_t col = 0; col < 3; ++col)
        maximum = std::max(maximum, panels[3*row+col].histogram->GetMaximum());
      for (std::size_t col = 0; col < 3; ++col) {
        auto& panel = panels[3*row+col]; auto& h = panel.histogram;
        canvas.cd(static_cast<int>(3*row+col+1));
        gPad->SetLeftMargin(0.17); gPad->SetRightMargin(0.23);
        gPad->SetBottomMargin(0.17); gPad->SetTopMargin(0.15); gPad->SetLogz();
        h->SetMinimum(2.0e-4); h->SetMaximum(maximum * 1.05);
        h->GetXaxis()->SetTitle("p_{T,e} [GeV]");
        h->GetYaxis()->SetTitle("log_{10}(t/GeV^{2})");
        h->GetZaxis()->SetTitle("Weighted events [%/bin]");
        for (auto* axis : {h->GetXaxis(), h->GetYaxis(), h->GetZaxis()}) {
          axis->SetTitleSize(0.055); axis->SetLabelSize(0.048);
        }
        h->GetXaxis()->SetTitleOffset(1.15); h->GetYaxis()->SetTitleOffset(1.4);
        h->GetZaxis()->SetTitleOffset(1.45); h->Draw("COLZ");
        text.SetTextSize(0.059); text.DrawLatexNDC(0.17, 0.94, panel.display.c_str());
        text.SetTextSize(0.050);
        text.DrawLatexNDC(0.17, 0.875, row == 0 ? "m_{#phi} = 1 GeV" : "m_{#phi} = 10 GeV");
      }
    }
    canvas.SaveAs((media / "figure.png").c_str());
    canvas.SaveAs((media / "figure.pdf").c_str());
    std::cout << "Read all six panels from the saved bins.\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n'; return 1;
  }
}
