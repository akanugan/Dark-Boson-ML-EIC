#define main mapping_diagnostic_unused_main
#include "diagnostics_mapping.cpp"
#undef main
#include <fstream>
#include <numeric>
std::vector<std::string> split(const std::string&s){std::vector<std::string> r;std::istringstream in(s);std::string t;while(std::getline(in,t,','))r.push_back(t);return r;}
int main(int argc,char**argv){
 if(argc!=4){std::cerr<<"Usage: diagnostics_support_widths mapping.csv cutmass output.csv\n";return 2;}
 Orig::GeneratorConfig cfg;cfg.mass=1e-6;cfg.cut_mass=std::stod(argv[2]);cfg.coupling=.3028221209;cfg.integrate_paper_cut=true;cfg.photon_region="all";Orig::VectorBosonDensity density(cfg);
 auto selected=[&](const std::array<double,4>&x){darkboson::EventKinematics e;double rho;return density.build_event(x.data(),e,rho)&&rho>0&&std::abs(e.boson_lab.Eta())>3.5;};
 std::ifstream in(argv[1]);std::ofstream out(argv[3]);std::string line;std::getline(in,line);auto h=split(line);std::array<int,4> col{};for(int j=0;j<4;++j)col[j]=std::find(h.begin(),h.end(),"cm_x"+std::to_string(j))-h.begin();
 out<<std::setprecision(17)<<"index,cm_x0,cm_x1,cm_x2,folded_x3,width_x0,width_x1,width_x2,width_x3,product_local_axis_widths\n";
 int n=0;while(std::getline(in,line)){
  auto vals=split(line);std::array<double,4>x{};for(int j=0;j<4;++j)x[j]=std::stod(vals.at(col[j]));if(!selected(x)){std::cerr<<"Initial point rejected\n";return 3;}
  double product=1;std::array<double,4> widths{};
  for(int j=0;j<4;++j){
   double extent[2]{};
   for(int direction=0;direction<2;++direction){
    double sign=direction?1:-1;double endpoint=direction?1-x[j]:x[j];
    // For periodic azimuth measure only one half-turn in each direction.
    if(j==3)endpoint=.5;
    double valid=0,invalid=std::min(1e-7,endpoint);bool failed=false;
    for(int k=0;k<70;++k){
     auto y=x;y[j]+=sign*invalid;if(j==3){if(y[j]<0)y[j]+=1;if(y[j]>1)y[j]-=1;}
     if(!selected(y)){failed=true;break;}valid=invalid;
     if(invalid>=endpoint)break;invalid=std::min(endpoint,invalid*1.6);
    }
    if(failed){for(int k=0;k<28;++k){double mid=(valid+invalid)/2;auto y=x;y[j]+=sign*mid;if(j==3){if(y[j]<0)y[j]+=1;if(y[j]>1)y[j]-=1;}if(selected(y))valid=mid;else invalid=mid;}}
    extent[direction]=valid;
   }
   widths[j]=extent[0]+extent[1];product*=widths[j];
  }
  out<<n++;for(int j=0;j<3;++j)out<<","<<x[j];out<<","<<2*std::min(x[3],1-x[3]);for(double v:widths)out<<","<<v;out<<","<<product<<"\n";
 }
 std::cout<<"Checked "<<n<<" local connected accepted neighborhoods\n";
}
