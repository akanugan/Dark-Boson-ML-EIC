#include <TFile.h>
#include <TTree.h>
#include <fstream>
#include <iomanip>
int main(int n,char** a){if(n!=3)return 2;TFile f(a[1]);auto*t=dynamic_cast<TTree*>(f.Get("events"));if(!t)return 1;double w,p,e;t->SetBranchAddress("foam_weight",&w);t->SetBranchAddress("electron_pt",&p);t->SetBranchAddress("electron_eta",&e);std::ofstream o(a[2]);o<<"weight,pt,eta\n"<<std::setprecision(17);for(Long64_t i=0;i<t->GetEntries();i++){t->GetEntry(i);o<<w<<','<<p<<','<<e<<'\n';}}
