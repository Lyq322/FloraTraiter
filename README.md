# FloraTraiter ![Python application](https://github.com/rafelafrance/FloraTraiter/workflows/CI/badge.svg)[![DOI](https://zenodo.org/badge/649758239.svg)](https://zenodo.org/badge/latestdoi/649758239)

**This repository is a fork of [FloraTraiter](https://github.com/rafelafrance/FloraTraiter).** The fork is mainly for **seed dispersal traits**: it adds scripts and options to analyze dispersal keywords (language frequencies, stats, pie charts), improves dispersal trait assignment for multilingual terms, and adds batch run scripts. See [Fork: additional features and usage](#fork-additional-features-and-usage) below.

## Note to people wanting to use these scripts.

These modules were written before the Large Language Model (LLM) revolution occurred. The most recent LLMs, even the smaller ones like Gemma3 etc., get you about (guessing) 90% of the way to what this set of scripts does, they often do it better, and they most definitely do it much with less work. LLMs are great at pattern recognition and that's all that these modules do. So, if you want to start a trait/information extraction project of your own I'd recommend that you consider a LLM-based approach first.

Rule-based parsing still has its uses for the next couple of years, albeit in a limited fashion, and with a lot less code than what I've generated here. I still use rules for:

1. Generating some test data. The code in this repository is way overkill for that.
2. Pre-processing text to get it into a format that gives LLMs an easier time of processing text. I do this less and less with each generation of LLMs.
3. Post-processing LLM results. Sometimes a LLM will give you results that are correct but not quite in a useful format. I'll sometimes use rule-based parsers to tweak LLM output. Nothing in this repository does this.

## Back to the regularly scheduled repository

Extract traits about plants from authoritative literature.

This repository merges three older repositories:
- `traiter_plants`
- `traiter_efloras`
- `traiter_mimosa`

And I also split some functionality out to enable me to use it in other projects.
- `pdf_parsers`: Scripts for parsing PDFs to prepare them for information extraction.
  - https://github.com/rafelafrance/pdf_parsers
- `LabelTraiter`: Parsing treatments (this repo) and herbarium labels are now separate repositories.
  - https://github.com/rafelafrance/LabelTraiter

I should also mention that this repository builds upon other repositories:
- `common_utils`: This is just a grab bag of simple utilities I used in several other project. I got tired of having to change every repository that used them each time there was an edit, so I just put them here.
  - `https://github.com/rafelafrance/common_utils`
- `spell-well`: Is a super simple "delete-only" spell checker I wrote. There may be better options now, but it survives until I can find one that handles our particular needs.
  - `https://github.com/rafelafrance/spell-well`
- `traiter`: This is the base code for all the rule-based parsers (aka traiters) that I write. The details change but the underlying process is the same for all.
  - `https://github.com/rafelafrance/traiter`

## All right, what's this all about then?
**Challenge**: Extract trait information from plant treatments. That is, if I'm given treatment text like: (Reformatted to emphasize targeted traits.)

![Treatment](assets/treatment.png)

I should be able to extract: (Colors correspond to the text above.)

![Traits](assets/traits.png)

## Terms
Essentially, we are finding relevant terms in the text (NER) and then linking them (Entity Linking). There are several types of terms:
1. The traits themselves: These are things like color, size, shape, woodiness, etc. They are either a measurement, count, or a member of a controlled vocabulary.
2. Plant parts: Things like leaves, branches, roots, seeds, etc. These have traits. So they must be linked to them.
3. Plant subparts: Things like hairs, pores, margins, veins, etc. Leaves can have hairs and so can seeds. They also have traits and will be linked to them, but they must also be linked to a part to have any meaning.
4. Sex: Plants exhibit sexual dimorphism, so we to note which part/subpart/trait notation is associated with which sex.
5. Other text: Things like conjunctions, punctuation, etc. Although they are not recorded, they are often important for parsing and linking of terms.

## Rule-based parsing strategy
1. I label terms using Spacy's phrase and rule-based matchers.
2. Then I match terms using rule-based matchers repeatedly until I have built up a recognizable trait like: color, size, count, etc.
3. Finally, I associate traits with plant parts.

For example, given the text: `Petiole 1-2 cm.`:
- I recognize vocabulary terms like:
    - `Petiole` is plant part
    - `1` a number
    - `-` a dash
    - `2` a number
    - `cm` is a unit notation
- Then I group tokens. For instance:
    - `1-2 cm` is a range with units which becomes a size trait.
- Finally, I associate the size with the plant part `Petiole` by using another pattern matching parser. Spacy will build a labeled sentence dependency tree. We look for patterns in the tree to link traits with plant parts.

There are, of course, complications and subtleties not outlined above, but you should get the gist of what is going on here.

## Install

You will need to have Python3.11+ installed, as well as pip, a package manager for Python.
You can install the requirements into your python environment like so:
```bash
git clone https://github.com/rafelafrance/FloraTraiter.git
cd FloraTraiter
make install
```

Every time you run any script in this repository, you'll have to activate the virtual environment once at the start of your session.

```bash
cd FloraTraiter
source .venv/bin/activate
```

### Extract traits

You'll need some treatment text files. One treatment per file.

Example:

```bash
parse-treatments --treatment-dir /path/to/treatments --json-dir /path/to/output/traits --html-file /path/to/traits.html
```

The output formats --json-dir & --html-file are optional. An example of the HTML output was shown above. An example of JSON output.

```json
{
    "dwc:scientificName": "Astragalus cobrensis A. Gray var. maguirei Kearney, | var. maguirei",
    "dwc:scientificNameAuthorship": "A. Gray | Kearney",
    "dwc:taxonRank": "variety",
    "dwc:dynamicProperties": {
        "fruitPart": "legume",
        "leafPart": "leaflet | leaf",
        "leafletHair": "hair",
        "leafletHairShape": "incurved-ascending",
        "leafletHairSize": "lengthLowInCentimeters: 0.06 ~ lengthHighInCentimeters: 0.08",
        "leafletHairSurface": "pilosulous",
        "legumeColor": "white",
        "legumeSurface": "villosulous",
        "partLocation": "adaxial"
    },
    "text": "..."
}
```

### Fork: additional features and usage

#### What’s in the fork

**Seed dispersal extraction**
- **`flora/pylib/rules/dispersal_traits.py`** – Extracts dispersal keywords (wing, pappus, fleshy reward, etc.), maps them to traits via `keyword_to_dispersal_traits_mapping.csv`, and supports negators and explicit absence terms.
- **`flora/pylib/rules/fruit_type.py`** – Fruit type (berry, capsule, legume, etc.) as a separate linkable rule.
- **`flora/pylib/writers/dispersal_format.py`** – Builds the `dispersal` block (`keywords_found`, traits as 0/1), filters by fruit/seed/fruit-type parts, and writes `dispersal_traits.csv`.
- **Pipeline & HTML** – DispersalTraits and FruitType added to the pipeline; seed dispersal traits highlighted in HTML output.

**Term vocabularies (multilingual)**
- Terms live under `flora/pylib/rules/terms/dispersal_terms/`: `dispersal_terms.csv`, `fruit_type_terms.csv`, `dispersal_negator_terms.csv`, `dispersal_absence_terms.csv`.
- Multilingual terms added (French, German, Latin, Spanish, Portuguese, Turkish). Part terms (`part_terms.csv`) extended with foreign-language seed/fruit words.

**Output and batching**
- JSON output includes a `dispersal` block and per–output-dir `dispersal_traits.csv`. `parse_treatments` can treat subdirs of `--treatment-dir` as batches and write per-batch HTML/CSV/JSON.

**Scripts and tooling**
- **`scripts/dispersal_keyword_stats.py`** – Language frequency of dispersal keywords, top keywords overall and per language, optional example file names.
- **`scripts/dispersal_keyword_piecharts.py`** – One image with one pie per subfolder (keyword language frequency), shared legend, full language names (needs `matplotlib`).
- **`plot_dispersal_traits.py`** – Plots presence/absence/unknown percent of traits (`pip install -r requirements-plot.txt`).

### Taxon database

A taxon database is included with the source code, but it may be out of date. I build a taxon database from 4 sources. The 3 primary sources each have various issues, but they complement each other well.

1. [ITIS sqlite database](https://www.itis.gov/downloads/index.html)
2. [The WFO Plant List](https://wfoplantlist.org/plant-list/classifications)
3. [Plant of the World Online](http://sftp.kew.org/pub/data-repositories/WCVP/)
4. [Some miscellaneous taxa not found in the other sources.](flora/pylib/rules/terms/other_taxa.csv)

Download the first 3 sources and then use the `util_add_taxa.py` script to extract the taxa and put them into a form the parsers can use.

## Tests

There are tests which you can run like so:
```bash
make test
```
