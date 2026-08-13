# Reference Guide — Why Each Source Is Used

This document maps each of the 42 references to the exact claim or passage it supports in the thesis.

---

## 1. Jurafsky & Martin — *Speech and Language Processing* (3rd ed.)
**URL:** https://web.stanford.edu/~jurafsky/slp3/ed3book_jan26.pdf  
**BibTeX key:** `jurafsky2024slp`  
**Used for:** General background on speech processing, language models, and HMM-based ASR pipelines (Ch. 1 Introduction & Ch. 2 Speech Processing Fundamentals). Specifically: the definition of the ASR pipeline (acoustic model + language model + decoder), MFCC feature extraction, and n-gram language models. See §9 (ASR) and §26 (Speech Synthesis) of the textbook.

---

## 2. Rabiner — *A Tutorial on Hidden Markov Models*
**URL:** https://www.cs.ubc.ca/~murphyk/Bayes/rabiner.pdf  
**BibTeX key:** `rabiner1989hmm`  
**Used for:** The theoretical foundation of the HMM-based ASR paradigm described in Ch. 4 (State of the Art). Cited when explaining the Baum-Welch algorithm, Viterbi decoding, and the three canonical HMM problems. See p. 257–286 of the paper.

---

## 3. Hinton et al. — *Deep Neural Networks for Acoustic Modeling*
**URL:** https://www.cs.toronto.edu/~hinton/absps/DNN-2012-proof.pdf  
**BibTeX key:** `hinton2012deep`  
**Used for:** The watershed result showing DNNs outperform GMM-HMMs on the TIMIT benchmark (Ch. 4 & Ch. 5). Cited for the claim: "replacing the GMM with a DNN in the HMM framework yielded dramatic WER reductions." See §4 (Experimental Results) and Table 1 in the paper.

---

## 4. Graves, Mohamed & Hinton — *Speech Recognition with Deep RNNs*
**URL:** https://www.cs.toronto.edu/~fritz/absps/RNN13.pdf  
**BibTeX key:** `graves2013speech`  
**Used for:** The Bidirectional LSTM + CTC model achieving SOTA on TIMIT (Ch. 5, RNN section). Cited for: "deep recurrent networks with CTC loss surpass feed-forward DNNs on phoneme recognition." See §3 and Table 1.

---

## 5. Hochreiter & Schmidhuber — *Long Short-Term Memory*
**URL:** https://www.researchgate.net/publication/13853244_Long_Short-Term_Memory  
**BibTeX key:** `hochreiter1997lstm`  
**Used for:** The original LSTM architecture definition (Ch. 3 Foundations & Ch. 5 Deep Learning Architectures). Cited when introducing the forget gate, input gate, output gate, and the cell state mechanism. See §2 (Constant Error Carousel) and §3 (LSTM).

---

## 6. Abdel-Hamid et al. — *Convolutional Neural Networks for Speech Recognition* (IEEE/ACM TASLP)
**URL:** https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/CNN_ASLPTrans2-14.pdf  
**BibTeX key:** `abdel2014cnn`  
**Used for:** Pioneering use of CNNs on spectrograms to capture local spectro-temporal patterns (Ch. 5). Cited for: "CNNs exploit local correlations in the frequency axis of filter-bank features." See §2 and Table II.

---

## 7. Vaswani et al. — *Attention Is All You Need* (NeurIPS 2017)
**URL:** https://proceedings.neurips.cc/paper_files/paper/2017/file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf  
**BibTeX key:** `vaswani2017attention`  
**Used for:** The Transformer architecture (multi-head self-attention, positional encoding, encoder-decoder) described in Ch. 3 and applied in Ch. 5 & Ch. 6. Cited for: "the Transformer dispensed with recurrence entirely, relying solely on attention." See §3 (Model Architecture).

---

## 8. Radford et al. — *Robust Speech Recognition via Large-Scale Weak Supervision* (Whisper)
**URL:** https://cdn.openai.com/papers/whisper.pdf  
**BibTeX key:** `radford2023whisper`  
**Used for:** The Whisper system (Ch. 4 SOTA & Ch. 6 End-to-End Systems). Cited for: "trained on 680,000 hours of weakly supervised multilingual audio, achieving strong zero-shot WER." See §2 (Approach) and Table 1 (LibriSpeech results).

---

## 9. Baevski et al. — *wav2vec 2.0* (NeurIPS 2020)
**URL:** https://proceedings.neurips.cc/paper/2020/file/92d1e1eb1cd6f9fba3227870bb6d7f07-Paper.pdf  
**BibTeX key:** `baevski2020wav2vec`  
**Used for:** The wav2vec 2.0 contrastive self-supervised learning framework (Ch. 4 & Ch. 6). Cited for: "quantized speech representations and contrastive loss enable pre-training from unlabelled audio." See §2 and Table 1 (1h/10min fine-tuning results).

---

## 10. Gulati et al. — *Conformer* (Interspeech 2020)
**URL:** https://www.isca-archive.org/interspeech_2020/gulati20_interspeech.pdf  
**BibTeX key:** `gulati2020conformer`  
**Used for:** The Conformer architecture combining convolution and self-attention (Ch. 4, Ch. 5 & Ch. 7 Comparative Analysis). Cited for: "achieves 1.9%/3.9% WER on LibriSpeech test-clean/test-other." See §2 (Conformer Block) and Table 1.

---

## 11. Graves et al. — *CTC: Labelling Unsegmented Sequence Data* (ICML 2006)
**URL:** https://people.idsia.ch/~santiago/papers/icml2006.pdf  
**BibTeX key:** `graves2006ctc`  
**Used for:** The original Connectionist Temporal Classification algorithm (Ch. 3 & Ch. 5). Cited when defining the CTC forward-backward algorithm and the blank label. See §3 (CTC) and the proof of the forward algorithm.

---

## 12. Park et al. — *SpecAugment* (Interspeech 2019)
**URL:** https://www.isca-archive.org/interspeech_2019/park19e_interspeech.pdf  
**BibTeX key:** `park2019specaugment`  
**Used for:** Data augmentation by masking frequency bands and time steps (Ch. 2 & Ch. 3). Cited for: "SpecAugment masks consecutive time steps and frequency channels, reducing overfitting." See §2 (Augmentation Policy) and Table 1.

---

## 13. Kingma & Ba — *Adam: A Method for Stochastic Optimization*
**URL:** https://www.intel.com/content/dam/www/public/us/en/ai/documents/1412.6980.pdf  
**BibTeX key:** `kingma2015adam`  
**Used for:** The Adam optimizer used to train all deep learning models discussed in Ch. 3. Cited for: "Adam adapts learning rates per-parameter using first and second moment estimates." See §2 (Algorithm 1) and §6 (Experiments).

---

## 14. Dahl et al. — *Context-Dependent Pre-Trained DNNs for LVCSR*
**URL:** https://www.cs.toronto.edu/~gdahl/papers/DBN4LVCSR-TransASLP.pdf  
**BibTeX key:** `dahl2012context`  
**Used for:** The DNN-HMM hybrid system outperforming GMM-HMMs on Bing Voice Search (Ch. 4 & Ch. 5). Cited for: "context-dependent DNN-HMM reduced WER by 16% relative over the best GMM-HMM." See §4 and Table I.

---

## 15. Sainath et al. — *Deep CNNs for LVCSR* (ICASSP 2013)
**URL:** https://www.cs.toronto.edu/~asamir/papers/icassp13_cnn.pdf  
**BibTeX key:** `sainath2015cnn`  
**Used for:** Deep CNN architectures for large-vocabulary ASR outperforming DNNs (Ch. 5). Cited for: "multiple convolutional layers with max-pooling reduce WER on the Switchboard benchmark." See §3 (Architecture) and Table I.

---

## 16. Cho et al. — *Learning Phrase Representations using RNN Encoder-Decoder* (GRU paper)
**URL:** https://arxiv.org/pdf/1406.1078  
**BibTeX key:** `cho2014gru`  
**Used for:** The GRU architecture as a simpler alternative to LSTM (Ch. 3 & Ch. 5). Cited for: "the GRU merges the forget and input gates into a single update gate." See §2 (RNN Encoder-Decoder) and §3.

---

## 17. Bahdanau, Cho & Bengio — *Neural Machine Translation by Jointly Learning to Align*
**URL:** https://arxiv.org/pdf/1409.0473  
**BibTeX key:** `bahdanau2015attention`  
**Used for:** The original attention mechanism (soft alignment) adapted to speech (Ch. 3 & Ch. 5). Cited for: "additive attention computes alignment scores as a learned function of encoder hidden states." See §3 (Attention) and Figure 3.

---

## 18. Chorowski et al. — *Attention-Based Models for Speech Recognition*
**URL:** https://arxiv.org/pdf/1506.07503  
**BibTeX key:** `chorowski2015attention`  
**Used for:** Applying Bahdanau attention directly to speech sequences (Ch. 5). Cited for: "location-sensitive attention uses the previous alignment to constrain where to attend next." See §2.2 and Table 1.

---

## 19. Chan et al. — *Listen, Attend and Spell*
**URL:** https://arxiv.org/pdf/1508.01211  
**BibTeX key:** `chan2016las`  
**Used for:** The first purely end-to-end encoder-attention-decoder ASR system (Ch. 5 & Ch. 6). Cited for: "LAS decodes character sequences directly from filterbank features without any HMM." See §2 (Model) and §4 (Experiments).

---

## 20. Hannun et al. — *Deep Speech: Scaling up End-to-End Speech Recognition*
**URL:** https://arxiv.org/pdf/1412.5567  
**BibTeX key:** `hannun2014deepspeech`  
**Used for:** The DeepSpeech 1 system using CTC on raw spectrogram features (Ch. 4 & Ch. 5). Cited for: "an end-to-end RNN-CTC model trained on 5,000 hours outperforms prior SOTA." See §3 and Table 1.

---

## 21. Amodei et al. — *Deep Speech 2*
**URL:** https://arxiv.org/pdf/1512.02595  
**BibTeX key:** `amodei2016deepspeech2`  
**Used for:** DeepSpeech 2 scaling to English and Mandarin (Ch. 4 & Ch. 5). Cited for: "batch normalization and SortaGrad training stabilize very deep RNN-CTC models." See §2 and Table 2.

---

## 22. Dong, Xu & Xu — *Speech-Transformer* (ICASSP 2018)
**URL:** https://houwx.net/files/papers/others/2018_icassp_speech_transformer.pdf  
**BibTeX key:** `dong2018speech`  
**Used for:** First direct application of the Transformer to ASR without recurrence (Ch. 5). Cited for: "2D attention on a 2D input representation captures both time and frequency contexts." See §2 and Table 1.

---

## 23. Zhang et al. — *Transformer Transducer* (Interspeech 2020)
**URL:** https://arxiv.org/pdf/2002.02562  
**BibTeX key:** `zhang2020transformerasr`  
**Used for:** The Transformer Transducer streaming architecture (Ch. 5 & Ch. 7). Cited for: "replacing LSTM encoder with Transformer in RNN-T enables streaming with low latency." See §2 and Table 1.

---

## 24. Hsu et al. — *HuBERT* (IEEE TASLP 2021)
**URL:** https://arxiv.org/pdf/2106.07447  
**BibTeX key:** `hsu2021hubert`  
**Used for:** Offline clustering + masked prediction self-supervised learning (Ch. 4 & Ch. 6). Cited for: "HuBERT predicts offline cluster IDs for masked frames, learning semantic representations." See §2 and Table 2.

---

## 25. Zhang et al. — *Google USM* (arXiv 2303.01037)
**URL:** https://arxiv.org/pdf/2303.01037  
**BibTeX key:** `zhang2022bigssl`  
**Used for:** Scaling ASR to 100+ languages (Ch. 4 SOTA). Cited for: "Google USM pre-trains a 2B-parameter model on 12M hours of audio spanning 300 languages." See §3 and Table 3.

---

## 26. Pratap et al. — *Scaling Speech Technology to 1,000+ Languages* (MMS)
**URL:** https://arxiv.org/pdf/2305.13516  
**BibTeX key:** `pratap2023mms`  
**Used for:** Meta's Massively Multilingual Speech model (Ch. 4 SOTA). Cited for: "MMS fine-tunes wav2vec 2.0 on New Testament recordings to cover 1,107 languages." See §3 and Table 4.

---

## 27. Ramirez et al. — *Anatomy of Industrial Scale Multilingual ASR* (AssemblyAI)
**URL:** https://arxiv.org/pdf/2404.09841  
**BibTeX key:** `assemblyai2024universal1`  
**Used for:** The Universal-1 Conformer RNN-T architecture details (Ch. 4 SOTA). Cited for: "600M-parameter Conformer RNN-T with BEST-RQ pre-training and a repeat token." See §2 (Architecture) and §4 (Results).

---

## 28. AssemblyAI Research — *Universal-2* (kept as-is)
**BibTeX key:** `assemblyai2024universal2`  
**Used for:** Universal-2 product-level improvements described in Ch. 4 SOTA.

---

## 29. Graves — *Sequence Transduction with Recurrent Neural Networks* (RNN-T)
**URL:** https://arxiv.org/pdf/1211.3711  
**BibTeX key:** `graves2012sequence`  
**Used for:** The original RNN-Transducer formulation (Ch. 5 & Ch. 6). Cited for: "RNN-T uses a prediction network conditioned on previous non-blank outputs to enable streaming." See §2 (Transducer) and §4.

---

## 30. Chiu et al. — *Self-Supervised Learning with Random-Projection Quantizer* (BEST-RQ)
**URL:** https://arxiv.org/pdf/2202.01855  
**BibTeX key:** `chiu2022bestrq`  
**Used for:** The BEST-RQ pre-training method used in AssemblyAI Universal models (Ch. 4). Cited for: "a random projection quantizer with no learned codebook achieves near wav2vec 2.0 quality." See §2 (Method) and Table 1.

---

## 31. Khare et al. — *Universal-2-TF: Robust All-Neural Text Formatting for ASR*
**URL:** https://arxiv.org/pdf/2501.05948  
**BibTeX key:** `assemblyai2025universal2tf`  
**Used for:** Neural text formatting pipeline in Universal-2 (Ch. 4 SOTA). Cited for: "a two-stage sequence-to-sequence model replaces rule-based capitalization and punctuation." See §2 (Architecture) and §4.

---

## 32. AssemblyAI Research — *Universal-3 Pro* (kept as-is)
**BibTeX key:** `assemblyai2026universal3`  
**Used for:** Promptable speech recognition (Ch. 4 SOTA).

---

## 33. Watanabe et al. — *ESPnet: End-to-End Speech Processing Toolkit*
**URL:** https://arxiv.org/pdf/1804.00015  
**BibTeX key:** `watanabe2018espnet`  
**Used for:** Open-source benchmark framework comparisons (Ch. 4 SOTA comparison table). Cited for: "ESPnet unifies CTC, attention, and hybrid CTC-attention training under one framework." See §2 (Architecture) and Table 1.

---

## 34. Sak, Senior & Beaufays — *LSTM RNN Architectures for Large Scale Acoustic Modeling*
**URL:** https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/43905.pdf  
**BibTeX key:** `sak2014long`  
**Used for:** LSTM-based acoustic models applied to large-vocabulary ASR (Ch. 5). Cited for: "a projected LSTM reduces parameters while maintaining accuracy on 3M-word vocabulary tasks." See §2 (LSTMP Architecture) and §5.

---

## 35. Kim, Hori & Watanabe — *Joint CTC-Attention End-to-End Speech Recognition*
**URL:** https://arxiv.org/pdf/1609.06773  
**BibTeX key:** `kim2017joint`  
**Used for:** The multi-task CTC + attention training strategy (Ch. 5 & Ch. 7). Cited for: "CTC acts as a monotonic alignment regularizer that speeds convergence of the attention decoder." See §2 and Table 1.

---

## 36. He et al. — *Streaming End-to-End Speech Recognition for Mobile Devices*
**URL:** https://arxiv.org/pdf/1811.06621  
**BibTeX key:** `he2019streaming`  
**Used for:** On-device streaming RNN-T (Ch. 6 & Ch. 7 deployment discussion). Cited for: "RNN-T achieves <100ms latency on a Pixel phone with quantized weights." See §2 (On-Device) and Table 4.

---

## 37. Schneider et al. — *wav2vec: Unsupervised Pre-Training for Speech Recognition*
**URL:** https://arxiv.org/pdf/1904.05862  
**BibTeX key:** `schneider2019wav2vec`  
**Used for:** The original wav2vec (v1) contrastive pre-training (Ch. 6). Cited for: "wav2vec learns raw waveform representations using a future-step prediction task." See §2 and Table 2.

---

## 38. Conneau et al. — *Unsupervised Cross-lingual Representation Learning* (XLSR-53)
**URL:** https://arxiv.org/pdf/2006.13979  
**BibTeX key:** `conneau2020xlsr`  
**Used for:** Cross-lingual transfer for low-resource Arabic ASR (Ch. 6 & Ch. 7). Cited for: "XLSR-53 trains a single wav2vec 2.0 on 53 languages, enabling transfer to unseen languages." See §3 and Table 4.

---

## 39. Panayotov et al. — *LibriSpeech: An ASR Corpus Based on Public Domain Audio Books*
**URL:** https://www.danielpovey.com/files/2015_icassp_librispeech.pdf  
**BibTeX key:** `panayotov2015librispeech`  
**Used for:** The standard English ASR benchmark dataset (Ch. 2 Datasets & Ch. 7 Experimental Methodology). Cited when stating WER figures on test-clean/test-other splits. See §2 (Corpus Description) and Table 2.

---

## 40. Biadsy, Hirschberg & Habash — *Spoken Arabic Dialect Identification*
**URL:** https://aclanthology.org/W09-0807.pdf  
**BibTeX key:** `biadsy2009spoken`  
**Used for:** Arabic dialect variation as a challenge for ASR (Ch. 7 Arabic/Darja section). Cited for: "phonotactic models distinguish MSA, Egyptian, Levantine, and Gulf dialects with >80% accuracy." See §3 and Table 2.

---

## 41. Maamouri et al. — *Developing and Using a Pilot Dialectal Arabic Treebank*
**URL:** http://www.lrec-conf.org/proceedings/lrec2006/pdf/543_pdf.pdf  
**BibTeX key:** `maamouri2006developing`  
**Used for:** The scarcity of annotated dialectal Arabic corpora (Ch. 7). Cited for: "annotating dialectal Arabic requires specialized tagsets distinct from MSA due to different morphology." See §2 (Treebank Design) and §4.

---

## 42. Amazouz, Adda-Decker & Adda — *Addressing Code-Switching in French/Algerian Arabic*
**URL:** https://shs.hal.science/halshs-01969148/file/Addressing_Code-Switching_in_FrenchAlgerian_Arabic.pdf  
**BibTeX key:** `amazouz2018addressing`  
**Used for:** Code-switching between French and Algerian Darja as a key ASR challenge (Ch. 7). Cited for: "intra-sentential French-Arabic switching creates acoustic mismatches that degrade ASR WER by 30%+." See §3 (Corpus) and §5 (Results).

---

*Generated automatically from the thesis bibliography on 2026-06-20.*
