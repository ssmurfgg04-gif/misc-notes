README: vtuad_strict_wav_vessel.zip byte-split parts
====================================================

`vtuad_strict_wav_vessel.zip` (509 strict-interval vessel clips, deflate)
is uploaded as three equal byte-split parts because of its size:

  vtuad_strict_wav_vessel.zip.part01  1,237,445,900 bytes
  vtuad_strict_wav_vessel.zip.part02  1,237,445,900 bytes
  vtuad_strict_wav_vessel.zip.part03  1,237,445,899 bytes

Reassembly (concatenate in order, then unzip normally):

  Windows (cmd):   copy /b vtuad_strict_wav_vessel.zip.part01 + vtuad_strict_wav_vessel.zip.part02 + vtuad_strict_wav_vessel.zip.part03 vtuad_strict_wav_vessel.zip
  Linux / macOS:   cat vtuad_strict_wav_vessel.zip.part01 vtuad_strict_wav_vessel.zip.part02 vtuad_strict_wav_vessel.zip.part03 > vtuad_strict_wav_vessel.zip

Integrity check of the restored archive (must match):

  SHA-256: 96564721a917d8b4dd161fdb90c66db917136786e6f4680028be6c6e03cf8ac6
  Size:    3,712,337,699 bytes

Per-part SHA-256 values are listed in this record's top-level
`SHA256SUMS.txt`; per-clip SHA-256 values of the WAVs inside the archive
are listed in `strict_interval_wav_SHA256SUMS.txt`.
