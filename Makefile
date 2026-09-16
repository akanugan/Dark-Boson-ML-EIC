ROOT_CONFIG ?= root-config
CXX ?= c++

CXXFLAGS := -std=c++17 -O3 -Wall -Wextra -Wpedantic \
	$(shell $(ROOT_CONFIG) --cflags) -Iinclude -I/opt/homebrew/include
LDLIBS := $(shell $(ROOT_CONFIG) --libs) -lPhysics -lTree -lHist -lFoam -lASImage
TMVA_LIBS := $(LDLIBS) -lTMVA

TARGETS := bin/generate_vector bin/generate_scalar bin/extract_cutflow bin/train_tmva bin/optimize_rectangular bin/optimize_rectangular_fair bin/evaluate_fair_model bin/plot_results bin/validate_photon_shapes bin/validate_sealed_sample

.PHONY: all plot clean

all: $(TARGETS)

bin/generate_vector: src/generate_vector.cpp include/DarkBosonKinematics.h
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

bin/generate_scalar: src/generate_scalar.cpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

bin/extract_cutflow: src/extract_cutflow.cpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

bin/train_tmva: src/train_tmva.cpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@ $(TMVA_LIBS)

bin/optimize_rectangular: src/optimize_rectangular.cpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

bin/optimize_rectangular_fair: src/optimize_rectangular_fair.cpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

bin/evaluate_fair_model: src/evaluate_fair_model.cpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@ $(TMVA_LIBS)

bin/plot_results: src/plot_results.cpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

bin/validate_photon_shapes: src/validate_photon_shapes.cpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

bin/validate_sealed_sample: src/validate_sealed_sample.cpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

plot:
	./scripts/reproduce_plot.sh

clean:
	rm -f $(TARGETS)
