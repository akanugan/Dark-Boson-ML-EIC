# Particles publication draft

From the project root, run `make paper`, or double-click `build.command` in this folder. The compiled PDF is `paper/latex/main.pdf`; temporary build files stay in `paper/latex/build/`. You can also run `./build.sh` from this folder.

Open `main.tex`, or upload the complete ZIP to Overleaf with `main.tex` as the main document. Compile using pdfLaTeX twice from this directory:

```sh
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The package includes the supplied MDPI ACS Definitions directory, all 10 embedded Word figures, 3 native LaTeX tables, 8 bibliography entries, linked citations and cross-references, and the compiled preview. No BibTeX step is required because the bibliography is embedded in main.tex.

## Sources and editorial scope

- Manuscript: `/Users/rojaemighty/Dark/paper/ML Paper.docx`.
- Template: `/Users/rojaemighty/Dark/MDPI_template_ACS/`, located after the supplied Downloads path was found missing. The supplied class is dated 31 August 2026.
- Formatting guidance: the supplied pasted Particles instructions for authors.

The manuscript's scientific results and limitations were retained. The abstract was condensed to 176 whitespace-delimited words; equations and notation were typeset, captions were attached to native floats, and missing publication metadata was marked explicitly. Research claims, reference metadata, statistical calculations, and the availability of the described project package have not been independently validated. Images are the original embedded PNGs; they were not regenerated or upscaled. The Word original was not modified.

## Complete before submission

- Replace all `\authorTODO{...}` fields: affiliation, correspondence email, funding, and the repository URL/DOI and access terms.
- Confirm the author contribution, conflict, acknowledgment, and not-applicable ethics statements.
- Check all eight reference records against their final publications; entries were transcribed from the manuscript. References 5–8 are listed in the source but have no explicit numbered citation in its body; add appropriate in-text citations after checking their relevance.
- Confirm the availability of supporting data, configuration details, and records supporting the manuscript's preregistration and checksum statements.
- Review the condensed abstract and determine whether the journal requires a disclosure of AI assistance for this editorial work or any earlier research assistance.
- The MDPI submit class prints provisional journal metadata and “submitted to Particles” automatically. These are template placeholders; no submission or publication has been performed.
