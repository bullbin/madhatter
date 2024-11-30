## madhatter

madhatter is a lower-level library for working with data formats compatible with earlier Professor Layton games for Nintendo DS.

## What can madhatter do?
 - Asset compression and decompression via LZ77, RLE and Huffman (both 4-bit and 8-bit) schemes with support for automatic NDS header creation ready for interfacing directly with stored ROM data
 - Decoding and encoding of a variety of formats from Professor Layton and the Curious Village (LAYTON1) up to Professor Layton and the Unwound Future (LAYTON3) with particularly complete support for Professor Layton and the Diabolical Box (LAYTON2)
 - Conversion to and from native formats for graphical formats, alongside an improved imaging pipeline for nicer paletting, quantization and transparencies
 

## What games does madhatter support?
||LAYTON1|LAYTON2|LAYTON2HD|LAYTON3|
|--|--|--|--|--|
|Assets|Unpack, compress|Unpack, compress|-|Unpack, compress
|Archives|Unpack, compress|Unpack, compress|n/a|Unpack, compress
|Scripting|Decode|Encode, decode|Encode, decode|Decode
|TalkScripts|n/a|Encode, decode|-|n/a
|Animation|Encode, decode|Encode, decode|Decode|Decode
|Backgrounds|Encode, decode|Encode, decode|unnecessary|Encode, decode
|Databases|n/a|Encode, decode|Encode, decode|n/a
|Packed databases|n/a|Encode, decode|Encode, decode|n/a
|Savefiles|-|Encode, sign, decode|-|-
|Rooms|Decode|Encode, decode|Encode, decode|n/a
|Puzzles|Encode, decode|Encode, decode|Encode, decode|n/a
|Audio|-|-|-|-
|Video|-|-|unnecessary|-

## So what can't madhatter do?

madhatter is a low-level library for working with pre-extracted assets; other than sanity checks it doesn't apply any engine-specific knowledge to prevent bad files from being created. For example, madhatter will not stop you from creating a puzzle that links to invalid assets or stop you from creating scripts with bad operands. madhatter provides minimal protections against underflow or overflow so try to provide santised inputs where possible.

## How do I install this?
madhatter is designed to be imported as-is with the folder. The easiest way to deploy it is as a submodule, as it can be synced and immediately used without messing with folders or redirects.

To install this, using a command line running in the same folder as madhatter, run

```
pip install -r requirements.txt
```

## How do I use this?

As madhatter was previously internal, there isn't great documentation for modifying assets. The current API for madhatter can be convoluted due to the codebase being older in some areas than others but it is capable - it is what widebrim and the widebrim editors are based on! A wiki of examples is in progress! There are plenty docstrings and function signatures to help in the meantime. If you can't figure out how to use it or need additional help, feel free to drop an issue on GitHub.

## I'm sold, who do I thank for this?
madhatter is a continuation of shortbrim except I had the time to reverse engineer the ROM. The following were really important in getting this project to where it is now:
- Tinke for initial research on imaging formats and LAYTON2 datatypes
- DSDecmp for NDS compression and decompression routines
- nocash for their excellent GBATEK hardware documentation
