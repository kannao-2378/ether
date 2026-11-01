# Course data sources

The application is not an official Oxford, British Council, ECDICT or Tatoeba course.
The 3,000 selected expressions are dictionary entries attested in independently
translated sentences. Corpus occurrence counts refer only to the downloaded
snapshot, not to a general-English frequency ranking. Automated syntax annotations
and topic assignments have not received item-by-item expert review.

## ECDICT

- Source: https://github.com/skywind3000/ECDICT
- License: MIT; full upstream notice is retained in `ecdict/LICENSE`.
- Used fields: headwords, translations, English definitions, inflections, source
  pronunciation (not assumed American), and explicit root-example associations.
- The project's README describes aggregation from multiple lexical sources; it is
  not an official publisher-authored curriculum.

## Tatoeba bilingual examples

- Project: https://tatoeba.org/
- Downloaded snapshot: https://huggingface.co/datasets/bdx33/tatoeba-hsk-cmn-eng-fra
- Declared license: CC BY 2.0; https://creativecommons.org/licenses/by/2.0/fr/
- English and Mandarin sentence IDs are retained for every selected example, with
  links to both original pages and their contributor information. The supplied
  snapshot lacks contributor usernames; no names have been invented.
- Definitions and sentence translations can contain errors. Selection verifies
  exact dictionary/corpus overlap, not universal grammatical or semantic accuracy.
- The 2,000-example auxiliary snapshot is from Apache SINGA's example directory:
  https://github.com/apache/singa/tree/master/examples/trans/cmn-eng . It is not
  used to fill the 3,000-expression compilation.

## CMU Pronouncing Dictionary

- Source: https://github.com/cmusphinx/cmudict
- Upstream license is retained in `cmudict/LICENSE`.
- ARPAbet readings are converted locally to phonemic segment notation. Syllable
  counts and stress positions come from the vowel/stress codes. Multiword items
  show component-word readings; these are not connected-speech recordings.

## Curriculum and explanations

- Topic groupings, progression, and short teaching notes are project-authored.
- Grammar reference: https://learnenglish.britishcouncil.org/free-resources/grammar
- Existing manually authored introductory notes are preserved.
- spaCy `en_core_web_sm` is an offline build-time annotator, not an online teacher.
- Source SHA-256 hashes and selection description are embedded in the compiled
  course manifest. Runtime installation requires no model API or network request.
