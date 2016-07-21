/*
 * This Python extension module implements LZW encoder and decoder
 * functions that are derived by Pearu Peterson in June 2010 from TIFF
 * Library tif_lzw.c code. See copyright notices below for more
 * information about the original authors of this software.
 */

/*
 * Copyright (c) 1988-1997 Sam Leffler
 * Copyright (c) 1991-1997 Silicon Graphics, Inc.
 *
 * Permission to use, copy, modify, distribute, and sell this software and 
 * its documentation for any purpose is hereby granted without fee, provided
 * that (i) the above copyright notices and this permission notice appear in
 * all copies of the software and related documentation, and (ii) the names of
 * Sam Leffler and Silicon Graphics may not be used in any advertising or
 * publicity relating to the software without the specific, prior written
 * permission of Sam Leffler and Silicon Graphics.
 * 
 * THE SOFTWARE IS PROVIDED "AS-IS" AND WITHOUT WARRANTY OF ANY KIND, 
 * EXPRESS, IMPLIED OR OTHERWISE, INCLUDING WITHOUT LIMITATION, ANY 
 * WARRANTY OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.  
 * 
 * IN NO EVENT SHALL SAM LEFFLER OR SILICON GRAPHICS BE LIABLE FOR
 * ANY SPECIAL, INCIDENTAL, INDIRECT OR CONSEQUENTIAL DAMAGES OF ANY KIND,
 * OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
 * WHETHER OR NOT ADVISED OF THE POSSIBILITY OF DAMAGE, AND ON ANY THEORY OF 
 * LIABILITY, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE 
 * OF THIS SOFTWARE.
 */

//#include "tiffiop.h"
//#ifdef LZW_SUPPORT

/*
 * TIFF Library.  
 * Rev 5.0 Lempel-Ziv & Welch Compression Support
 *
 * This code is derived from the compress program whose code is
 * derived from software contributed to Berkeley by James A. Woods,
 * derived from original work by Spencer Thomas and Joseph Orost.
 *
 * The original Berkeley copyright notice appears below in its entirety.
 */


#include <Python.h>
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#define PY_ARRAY_UNIQUE_SYMBOL PyArray_API
#include "numpy/arrayobject.h"

#ifndef PyMODINIT_FUNC  /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K
#endif

typedef signed int tmsize_t;
typedef tmsize_t tsize_t;
typedef npy_uint8 uint8;
typedef npy_uint16 uint16;

typedef struct {
  uint8*               tif_data;         /* compression scheme private data */
  uint8*               tif_rawdata;      /* raw data buffer */
  tmsize_t             tif_rawdatasize;  /* # of bytes in raw data buffer */
  uint8*               tif_rawcp;        /* current spot in raw buffer */
  tmsize_t             tif_rawcc;        /* bytes unread from raw buffer */  
} TIFF;

//#include "tif_predict.h"

#include <stdio.h>

/*
 * NB: The 5.0 spec describes a different algorithm than Aldus
 *     implements.  Specifically, Aldus does code length transitions
 *     one code earlier than should be done (for real LZW).
 *     Earlier versions of this library implemented the correct
 *     LZW algorithm, but emitted codes in a bit order opposite
 *     to the TIFF spec.  Thus, to maintain compatibility w/ Aldus
 *     we interpret MSB-LSB ordered codes to be images written w/
 *     old versions of this library, but otherwise adhere to the
 *     Aldus "off by one" algorithm.
 *
 * Future revisions to the TIFF spec are expected to "clarify this issue".
 */
  //#define LZW_COMPAT              /* include backwards compatibility code */
/*
 * Each strip of data is supposed to be terminated by a CODE_EOI.
 * If the following #define is included, the decoder will also
 * check for end-of-strip w/o seeing this code.  This makes the
 * library more robust, but also slower.
 */
#define LZW_CHECKEOS            /* include checks for strips w/o EOI code */

#define MAXCODE(n)	((1L<<(n))-1)
/*
 * The TIFF spec specifies that encoded bit
 * strings range from 9 to 12 bits.
 */
#define BITS_MIN        9               /* start with 9 bits */
#define BITS_MAX        12              /* max of 12 bit strings */
/* predefined codes */
#define CODE_CLEAR      256             /* code to clear string table */
#define CODE_EOI        257             /* end-of-information code */
#define CODE_FIRST      258             /* first free code entry */
#define CODE_MAX        MAXCODE(BITS_MAX)
#define HSIZE           9001L           /* 91% occupancy */
#define HSHIFT          (13-8)
#ifdef LZW_COMPAT
/* NB: +1024 is for compatibility with old files */
#define CSIZE           (MAXCODE(BITS_MAX)+1024L)
#else
#define CSIZE           (MAXCODE(BITS_MAX)+1L)
#endif

/*
 * State block for each open TIFF file using LZW
 * compression/decompression.  Note that the predictor
 * state block must be first in this data structure.
 */
typedef struct {
  //	TIFFPredictorState predict;     /* predictor super class */

	unsigned short  nbits;          /* # of bits/code */
	unsigned short  maxcode;        /* maximum code for lzw_nbits */
	unsigned short  free_ent;       /* next free entry in hash table */
	long            nextdata;       /* next bits of i/o */
	long            nextbits;       /* # of valid bits in lzw_nextdata */

  //int             rw_mode;        /* preserve rw_mode from init */
} LZWBaseState;

#define lzw_nbits       base.nbits
#define lzw_maxcode     base.maxcode
#define lzw_free_ent    base.free_ent
#define lzw_nextdata    base.nextdata
#define lzw_nextbits    base.nextbits

/*
 * Encoding-specific state.
 */
typedef uint16 hcode_t;			/* codes fit in 16 bits */
typedef struct {
	long	hash;
	hcode_t	code;
} hash_t;

/*
 * Decoding-specific state.
 */
typedef struct code_ent {
	struct code_ent *next;
	unsigned short	length;		/* string len, including this token */
	unsigned char	value;		/* data value */
	unsigned char	firstchar;	/* first token of string */
} code_t;

//typedef int (*decodeFunc)(TIFF*, uint8*, tmsize_t, uint16);

typedef struct {
	LZWBaseState base;

	/* Decoding specific data */
	long    dec_nbitsmask;		/* lzw_nbits 1 bits, right adjusted */
	long    dec_restart;		/* restart count */
#ifdef LZW_CHECKEOS
	tmsize_t dec_bitsleft;		/* available bits in raw data */
#endif
  //decodeFunc dec_decode;		/* regular or backwards compatible */
	code_t* dec_codep;		/* current recognized code */
	code_t* dec_oldcodep;		/* previously recognized code */
	code_t* dec_free_entp;		/* next free entry */
	code_t* dec_maxcodep;		/* max available entry */
	code_t* dec_codetab;		/* kept separate for small machines */

	/* Encoding specific data */
	int     enc_oldcode;		/* last code encountered */
	long    enc_checkpoint;		/* point at which to clear table */
#define CHECK_GAP	10000		/* enc_ratio check interval */
	long    enc_ratio;		/* current compression ratio */
	long    enc_incount;		/* (input) data bytes encoded */
	long    enc_outcount;		/* encoded (output) bytes */
	uint8*  enc_rawlimit;		/* bound on tif_rawdata buffer */
	hash_t* enc_hashtab;		/* kept separate for small machines */
} LZWCodecState;

#define LZWState(tif)		((LZWBaseState*) (tif)->tif_data)
#define DecoderState(tif)	((LZWCodecState*) LZWState(tif))
#define EncoderState(tif)	((LZWCodecState*) LZWState(tif))

//static int LZWDecode(TIFF* tif, uint8* op0, tmsize_t occ0, uint16 s);
#ifdef LZW_COMPAT
static int LZWDecodeCompat(TIFF* tif, uint8* op0, tmsize_t occ0, uint16 s);
#endif
static void cl_hash(LZWCodecState*);

/*
 * LZW Decoder.
 */

#ifdef LZW_CHECKEOS
/*
 * This check shouldn't be necessary because each
 * strip is suppose to be terminated with CODE_EOI.
 */
#define	NextCode(_tif, _sp, _bp, _code, _get) {				\
	if ((_sp)->dec_bitsleft < (tmsize_t)nbits) {			\
	  /*TIFFWarningExt(_tif->tif_clientdata, module,*/		\
	  /*		    "LZWDecode: Strip %d not terminated with EOI code", */ \
	  /*	    _tif->tif_curstrip);*/				\
		_code = CODE_EOI;					\
	} else {							\
		_get(_sp,_bp,_code);					\
		(_sp)->dec_bitsleft -= nbits;				\
	}								\
}
#else
#define	NextCode(tif, sp, bp, code, get) get(sp, bp, code)
#endif

#if 1
static int
LZWSetupDecode(TIFF* tif)
{
	LZWCodecState* sp = DecoderState(tif);
	int code;

	if( sp == NULL )
	{
		/*
		 * Allocate state block so tag methods have storage to record
		 * values.
		*/
	  //tif->tif_data = (uint8*) TIFFmalloc(sizeof(LZWCodecState));
		tif->tif_data = (uint8*) malloc(sizeof(LZWCodecState));
		if (tif->tif_data == NULL)
		{
		  //TIFFErrorExt(tif->tif_clientdata, module, "No space for LZW state block");
			return (0);
		}

		DecoderState(tif)->dec_codetab = NULL;
		//DecoderState(tif)->dec_decode = NULL;

		/*
		 * Setup predictor setup.
		 */
		//(void) TIFFPredictorInit(tif);

		sp = DecoderState(tif);
	}

	assert(sp != NULL);

	if (sp->dec_codetab == NULL) {
	  //sp->dec_codetab = (code_t*)_TIFFmalloc(CSIZE*sizeof (code_t));
		sp->dec_codetab = (code_t*)malloc(CSIZE*sizeof (code_t));
		if (sp->dec_codetab == NULL) {
		  //TIFFErrorExt(tif->tif_clientdata, module,
		  //		     "No space for LZW code table");
			return (0);
		}
		/*
		 * Pre-load the table.
		 */
		code = 255;
		do {
			sp->dec_codetab[code].value = code;
			sp->dec_codetab[code].firstchar = code;
			sp->dec_codetab[code].length = 1;
			sp->dec_codetab[code].next = NULL;
		} while (code--);
		/*
		 * Zero-out the unused entries
                 */
		//_TIFFmemset(&sp->dec_codetab[CODE_CLEAR], 0,
		//     (CODE_FIRST - CODE_CLEAR) * sizeof (code_t));
		memset(&sp->dec_codetab[CODE_CLEAR], 0,
		       (CODE_FIRST - CODE_CLEAR) * sizeof (code_t));
	}
	return (1);
}

/*
 * Setup state for decoding a strip.
 */
static int
LZWPreDecode(TIFF* tif)
{
	LZWCodecState *sp = DecoderState(tif);

	//(void) s;
	assert(sp != NULL);
	if( sp->dec_codetab == NULL )
        {
	  //tif->tif_setupdecode( tif );
	    LZWSetupDecode(tif);
        }

	/*
	 * Check for old bit-reversed codes.
	 */
	if (tif->tif_rawdata[0] == 0 && (tif->tif_rawdata[1] & 0x1)) {
#ifdef LZW_COMPAT
		if (!sp->dec_decode) {
			TIFFWarningExt(tif->tif_clientdata, module,
			    "Old-style LZW codes, convert file");
			/*
			 * Override default decoding methods with
			 * ones that deal with the old coding.
			 * Otherwise the predictor versions set
			 * above will call the compatibility routines
			 * through the dec_decode method.
			 */
			tif->tif_decoderow = LZWDecodeCompat;
			tif->tif_decodestrip = LZWDecodeCompat;
			tif->tif_decodetile = LZWDecodeCompat;
			/*
			 * If doing horizontal differencing, must
			 * re-setup the predictor logic since we
			 * switched the basic decoder methods...
			 */
			(*tif->tif_setupdecode)(tif);
			sp->dec_decode = LZWDecodeCompat;
		}
		sp->lzw_maxcode = MAXCODE(BITS_MIN);
#else /* !LZW_COMPAT */
		//if (!sp->dec_decode) {
		  //TIFFErrorExt(tif->tif_clientdata, module,
		  //    "Old-style LZW codes not supported");
		//sp->dec_decode = LZWDecode;
		//}
		return (0);
#endif/* !LZW_COMPAT */
	} else {
		sp->lzw_maxcode = MAXCODE(BITS_MIN)-1;
		//sp->dec_decode = LZWDecode;
	}
	sp->lzw_nbits = BITS_MIN;
	sp->lzw_nextbits = 0;
	sp->lzw_nextdata = 0;

	sp->dec_restart = 0;
	sp->dec_nbitsmask = MAXCODE(BITS_MIN);
#ifdef LZW_CHECKEOS
	sp->dec_bitsleft = tif->tif_rawcc << 3;
#endif
	sp->dec_free_entp = sp->dec_codetab + CODE_FIRST;
	/*
	 * Zero entries that are not yet filled in.  We do
	 * this to guard against bogus input data that causes
	 * us to index into undefined entries.  If you can
	 * come up with a way to safely bounds-check input codes
	 * while decoding then you can remove this operation.
	 */
	//_TIFFmemset(sp->dec_free_entp, 0, (CSIZE-CODE_FIRST)*sizeof (code_t));
	memset(sp->dec_free_entp, 0, (CSIZE-CODE_FIRST)*sizeof (code_t));
	sp->dec_oldcodep = &sp->dec_codetab[-1];
	sp->dec_maxcodep = &sp->dec_codetab[sp->dec_nbitsmask-1];
	return (1);
}

/*
 * Decode a "hunk of data".
 */
#define	GetNextCode(sp, bp, code) {				\
	nextdata = (nextdata<<8) | *(bp)++;			\
	nextbits += 8;						\
	if (nextbits < nbits) {					\
		nextdata = (nextdata<<8) | *(bp)++;		\
		nextbits += 8;					\
	}							\
	code = (hcode_t)((nextdata >> (nextbits-nbits)) & nbitsmask);	\
	nextbits -= nbits;					\
}

static void
codeLoop(TIFF* tif)
{
  //TIFFErrorExt(tif->tif_clientdata, module,
  //    "Bogus encoding, loop in the code table; scanline %d",
  //    tif->tif_row);
}

static int
LZWDecode(TIFF* tif, uint8* op0, tmsize_t occ0)
{
	LZWCodecState *sp = DecoderState(tif);
	char *op = (char*) op0;
	long occ = (long) occ0;
	char *tp;
	unsigned char *bp;
	hcode_t code;
	int len;
	long nbits, nextbits, nextdata, nbitsmask;
	code_t *codep, *free_entp, *maxcodep, *oldcodep;

	//(void) s;
	assert(sp != NULL);
        assert(sp->dec_codetab != NULL);

	/*
	  Fail if value does not fit in long.
	*/
	if ((tmsize_t) occ != occ0)
	        return (0);
	/*
	 * Restart interrupted output operation.
	 */
	if (sp->dec_restart) {
		long residue;

		codep = sp->dec_codep;
		residue = codep->length - sp->dec_restart;
		if (residue > occ) {
			/*
			 * Residue from previous decode is sufficient
			 * to satisfy decode request.  Skip to the
			 * start of the decoded string, place decoded
			 * values in the output buffer, and return.
			 */
			sp->dec_restart += occ;
			do {
				codep = codep->next;
			} while (--residue > occ && codep);
			if (codep) {
				tp = op + occ;
				do {
					*--tp = codep->value;
					codep = codep->next;
				} while (--occ && codep);
			}
			return (1);
		}
		/*
		 * Residue satisfies only part of the decode request.
		 */
		op += residue, occ -= residue;
		tp = op;
		do {
			int t;
			--tp;
			t = codep->value;
			codep = codep->next;
			*tp = t;
		} while (--residue && codep);
		sp->dec_restart = 0;
	}

	bp = (unsigned char *)tif->tif_rawcp;
	nbits = sp->lzw_nbits;
	nextdata = sp->lzw_nextdata;
	nextbits = sp->lzw_nextbits;
	nbitsmask = sp->dec_nbitsmask;
	oldcodep = sp->dec_oldcodep;
	free_entp = sp->dec_free_entp;
	maxcodep = sp->dec_maxcodep;

	while (occ > 0) {
		NextCode(tif, sp, bp, code, GetNextCode);
		if (code == CODE_EOI)
			break;
		if (code == CODE_CLEAR) {
			free_entp = sp->dec_codetab + CODE_FIRST;
			//_TIFFmemset(free_entp, 0,
			//	    (CSIZE - CODE_FIRST) * sizeof (code_t));
			memset(free_entp, 0,
			       (CSIZE - CODE_FIRST) * sizeof (code_t));
			nbits = BITS_MIN;
			nbitsmask = MAXCODE(BITS_MIN);
			maxcodep = sp->dec_codetab + nbitsmask-1;
			NextCode(tif, sp, bp, code, GetNextCode);
			if (code == CODE_EOI)
				break;
			if (code >= CODE_CLEAR) {
			  //TIFFErrorExt(tif->tif_clientdata, tif->tif_name,
			  //"LZWDecode: Corrupted LZW table at scanline %d",
			  //	     tif->tif_row);
				return (0);
			}
			*op++ = (char)code, occ--;
			oldcodep = sp->dec_codetab + code;
			continue;
		}
		codep = sp->dec_codetab + code;

		/*
		 * Add the new entry to the code table.
		 */
		if (free_entp < &sp->dec_codetab[0] ||
		    free_entp >= &sp->dec_codetab[CSIZE]) {
		  //TIFFErrorExt(tif->tif_clientdata, module,
		  //    "Corrupted LZW table at scanline %d",
		  //    tif->tif_row);
			return (0);
		}

		free_entp->next = oldcodep;
		if (free_entp->next < &sp->dec_codetab[0] ||
		    free_entp->next >= &sp->dec_codetab[CSIZE]) {
		  //TIFFErrorExt(tif->tif_clientdata, module,
		  //    "Corrupted LZW table at scanline %d",
		  //    tif->tif_row);
			return (0);
		}
		free_entp->firstchar = free_entp->next->firstchar;
		free_entp->length = free_entp->next->length+1;
		free_entp->value = (codep < free_entp) ?
		    codep->firstchar : free_entp->firstchar;
		if (++free_entp > maxcodep) {
			if (++nbits > BITS_MAX)		/* should not happen */
				nbits = BITS_MAX;
			nbitsmask = MAXCODE(nbits);
			maxcodep = sp->dec_codetab + nbitsmask-1;
		}
		oldcodep = codep;
		if (code >= 256) {
			/*
			 * Code maps to a string, copy string
			 * value to output (written in reverse).
			 */
			if(codep->length == 0) {
			  //	TIFFErrorExt(tif->tif_clientdata, module,
			  //    "Wrong length of decoded string: "
			  //    "data probably corrupted at scanline %d",
			  //    tif->tif_row);
				return (0);
			}
			if (codep->length > occ) {
				/*
				 * String is too long for decode buffer,
				 * locate portion that will fit, copy to
				 * the decode buffer, and setup restart
				 * logic for the next decoding call.
				 */
				sp->dec_codep = codep;
				do {
					codep = codep->next;
				} while (codep && codep->length > occ);
				if (codep) {
					sp->dec_restart = (long)occ;
					tp = op + occ;
					do  {
						*--tp = codep->value;
						codep = codep->next;
					}  while (--occ && codep);
					if (codep)
						codeLoop(tif);
				}
				break;
			}
			len = codep->length;
			tp = op + len;
			do {
				int t;
				--tp;
				t = codep->value;
				codep = codep->next;
				*tp = t;
			} while (codep && tp > op);
			if (codep) {
			    codeLoop(tif);
			    break;
			}
			assert(occ >= len);
			op += len, occ -= len;
		} else
			*op++ = (char)code, occ--;
	}

	tif->tif_rawcp = (uint8*) bp;
	sp->lzw_nbits = (unsigned short) nbits;
	sp->lzw_nextdata = nextdata;
	sp->lzw_nextbits = nextbits;
	sp->dec_nbitsmask = nbitsmask;
	sp->dec_oldcodep = oldcodep;
	sp->dec_free_entp = free_entp;
	sp->dec_maxcodep = maxcodep;

	return (occ); // return extra bytes for resizing result array
}

#ifdef LZW_COMPAT
/*
 * Decode a "hunk of data" for old images.
 */
#define	GetNextCodeCompat(sp, bp, code) {			\
	nextdata |= (unsigned long) *(bp)++ << nextbits;	\
	nextbits += 8;						\
	if (nextbits < nbits) {					\
		nextdata |= (unsigned long) *(bp)++ << nextbits;\
		nextbits += 8;					\
	}							\
	code = (hcode_t)(nextdata & nbitsmask);			\
	nextdata >>= nbits;					\
	nextbits -= nbits;					\
}

static int
LZWDecodeCompat(TIFF* tif, uint8* op0, tmsize_t occ0, uint16 s)
{
	static const char module[] = "LZWDecodeCompat";
	LZWCodecState *sp = DecoderState(tif);
	char *op = (char*) op0;
	long occ = (long) occ0;
	char *tp;
	unsigned char *bp;
	int code, nbits;
	long nextbits, nextdata, nbitsmask;
	code_t *codep, *free_entp, *maxcodep, *oldcodep;

	(void) s;
	assert(sp != NULL);

	/*
	  Fail if value does not fit in long.
	*/
	if ((tmsize_t) occ != occ0)
	        return (0);

	/*
	 * Restart interrupted output operation.
	 */
	if (sp->dec_restart) {
		long residue;

		codep = sp->dec_codep;
		residue = codep->length - sp->dec_restart;
		if (residue > occ) {
			/*
			 * Residue from previous decode is sufficient
			 * to satisfy decode request.  Skip to the
			 * start of the decoded string, place decoded
			 * values in the output buffer, and return.
			 */
			sp->dec_restart += occ;
			do {
				codep = codep->next;
			} while (--residue > occ);
			tp = op + occ;
			do {
				*--tp = codep->value;
				codep = codep->next;
			} while (--occ);
			return (1);
		}
		/*
		 * Residue satisfies only part of the decode request.
		 */
		op += residue, occ -= residue;
		tp = op;
		do {
			*--tp = codep->value;
			codep = codep->next;
		} while (--residue);
		sp->dec_restart = 0;
	}

	bp = (unsigned char *)tif->tif_rawcp;
	nbits = sp->lzw_nbits;
	nextdata = sp->lzw_nextdata;
	nextbits = sp->lzw_nextbits;
	nbitsmask = sp->dec_nbitsmask;
	oldcodep = sp->dec_oldcodep;
	free_entp = sp->dec_free_entp;
	maxcodep = sp->dec_maxcodep;

	while (occ > 0) {
		NextCode(tif, sp, bp, code, GetNextCodeCompat);
		if (code == CODE_EOI)
			break;
		if (code == CODE_CLEAR) {
			free_entp = sp->dec_codetab + CODE_FIRST;
			_TIFFmemset(free_entp, 0,
				    (CSIZE - CODE_FIRST) * sizeof (code_t));
			nbits = BITS_MIN;
			nbitsmask = MAXCODE(BITS_MIN);
			maxcodep = sp->dec_codetab + nbitsmask;
			NextCode(tif, sp, bp, code, GetNextCodeCompat);
			if (code == CODE_EOI)
				break;
			if (code >= CODE_CLEAR) {
				TIFFErrorExt(tif->tif_clientdata, tif->tif_name,
				"LZWDecode: Corrupted LZW table at scanline %d",
					     tif->tif_row);
				return (0);
			}
			*op++ = code, occ--;
			oldcodep = sp->dec_codetab + code;
			continue;
		}
		codep = sp->dec_codetab + code;

		/*
		 * Add the new entry to the code table.
		 */
		if (free_entp < &sp->dec_codetab[0] ||
		    free_entp >= &sp->dec_codetab[CSIZE]) {
			TIFFErrorExt(tif->tif_clientdata, module,
			    "Corrupted LZW table at scanline %d", tif->tif_row);
			return (0);
		}

		free_entp->next = oldcodep;
		if (free_entp->next < &sp->dec_codetab[0] ||
		    free_entp->next >= &sp->dec_codetab[CSIZE]) {
			TIFFErrorExt(tif->tif_clientdata, module,
			    "Corrupted LZW table at scanline %d", tif->tif_row);
			return (0);
		}
		free_entp->firstchar = free_entp->next->firstchar;
		free_entp->length = free_entp->next->length+1;
		free_entp->value = (codep < free_entp) ?
		    codep->firstchar : free_entp->firstchar;
		if (++free_entp > maxcodep) {
			if (++nbits > BITS_MAX)		/* should not happen */
				nbits = BITS_MAX;
			nbitsmask = MAXCODE(nbits);
			maxcodep = sp->dec_codetab + nbitsmask;
		}
		oldcodep = codep;
		if (code >= 256) {
			/*
			 * Code maps to a string, copy string
			 * value to output (written in reverse).
			 */
			if(codep->length == 0) {
				TIFFErrorExt(tif->tif_clientdata, module,
				    "Wrong length of decoded "
				    "string: data probably corrupted at scanline %d",
				    tif->tif_row);
				return (0);
			}
			if (codep->length > occ) {
				/*
				 * String is too long for decode buffer,
				 * locate portion that will fit, copy to
				 * the decode buffer, and setup restart
				 * logic for the next decoding call.
				 */
				sp->dec_codep = codep;
				do {
					codep = codep->next;
				} while (codep->length > occ);
				sp->dec_restart = occ;
				tp = op + occ;
				do  {
					*--tp = codep->value;
					codep = codep->next;
				}  while (--occ);
				break;
			}
			assert(occ >= codep->length);
			op += codep->length, occ -= codep->length;
			tp = op;
			do {
				*--tp = codep->value;
			} while( (codep = codep->next) != NULL );
		} else
			*op++ = code, occ--;
	}

	tif->tif_rawcp = (uint8*) bp;
	sp->lzw_nbits = nbits;
	sp->lzw_nextdata = nextdata;
	sp->lzw_nextbits = nextbits;
	sp->dec_nbitsmask = nbitsmask;
	sp->dec_oldcodep = oldcodep;
	sp->dec_free_entp = free_entp;
	sp->dec_maxcodep = maxcodep;

	if (occ > 0) {
#if defined(__WIN32__) && defined(_MSC_VER)
		TIFFErrorExt(tif->tif_clientdata, module,
			"Not enough data at scanline %d (short %I64d bytes)",
			     tif->tif_row, (unsigned __int64) occ);
#else
		TIFFErrorExt(tif->tif_clientdata, module,
			"Not enough data at scanline %d (short %llu bytes)",
			     tif->tif_row, (unsigned long long) occ);
#endif
		return (0);
	}
	return (1);
}
#endif /* LZW_COMPAT */

#endif /* if 1 */
/*
 * LZW Encoding.
 */

static int
LZWSetupEncode(TIFF* tif)
{
  //static const char module[] = "LZWSetupEncode";
	LZWCodecState* sp = EncoderState(tif);

	assert(sp != NULL);
	//sp->enc_hashtab = (hash_t*) _TIFFmalloc(HSIZE*sizeof (hash_t));
	sp->enc_hashtab = (hash_t*) malloc(HSIZE*sizeof (hash_t));
	if (sp->enc_hashtab == NULL) {
	  //TIFFErrorExt(tif->tif_clientdata, module,
	  //	     "No space for LZW hash table");
		return (0);
	}
	return (1);
}

/*
 * Reset encoding state at the start of a strip.
 */
static int
LZWPreEncode(TIFF* tif/*, uint16 s*/)
{
	LZWCodecState *sp = EncoderState(tif);

	//(void) s;
	assert(sp != NULL);

	if( sp->enc_hashtab == NULL )
        {
	  //tif->tif_setupencode( tif );
	  LZWSetupEncode(tif);
        }

	sp->lzw_nbits = BITS_MIN;
	sp->lzw_maxcode = MAXCODE(BITS_MIN);
	sp->lzw_free_ent = CODE_FIRST;
	sp->lzw_nextbits = 0;
	sp->lzw_nextdata = 0;
	sp->enc_checkpoint = CHECK_GAP;
	sp->enc_ratio = 0;
	sp->enc_incount = 0;
	sp->enc_outcount = 0;
	/*
	 * The 4 here insures there is space for 2 max-sized
	 * codes in LZWEncode and LZWPostDecode.
	 */
	sp->enc_rawlimit = tif->tif_rawdata + tif->tif_rawdatasize-1 - 4;
	cl_hash(sp);		/* clear hash table */
	sp->enc_oldcode = (hcode_t) -1;	/* generates CODE_CLEAR in LZWEncode */
	return (1);
}

#define	CALCRATIO(sp, rat) {					\
	if (incount > 0x007fffff) { /* NB: shift will overflow */\
		rat = outcount >> 8;				\
		rat = (rat == 0 ? 0x7fffffff : incount/rat);	\
	} else							\
		rat = (incount<<8) / outcount;			\
}
#define	PutNextCode(op, c) {					\
	nextdata = (nextdata << nbits) | c;			\
	nextbits += nbits;					\
	*op++ = (unsigned char)(nextdata >> (nextbits-8));		\
	nextbits -= 8;						\
	if (nextbits >= 8) {					\
		*op++ = (unsigned char)(nextdata >> (nextbits-8));	\
		nextbits -= 8;					\
	}							\
	outcount += nbits;					\
}

/*
 * Encode a chunk of pixels.
 *
 * Uses an open addressing double hashing (no chaining) on the 
 * prefix code/next character combination.  We do a variant of
 * Knuth's algorithm D (vol. 3, sec. 6.4) along with G. Knott's
 * relatively-prime secondary probe.  Here, the modular division
 * first probe is gives way to a faster exclusive-or manipulation. 
 * Also do block compression with an adaptive reset, whereby the
 * code table is cleared when the compression ratio decreases,
 * but after the table fills.  The variable-length output codes
 * are re-sized at this point, and a CODE_CLEAR is generated
 * for the decoder. 
 */

#define FLUSHDATA(LST, DATA, DATASIZE) {					\
    npy_intp dims[] = {(DATASIZE)};					\
    PyObject *arr = PyArray_EMPTY(1, dims, NPY_UBYTE, 0);	\
    memcpy(PyArray_DATA((PyArrayObject*)arr), (DATA), dims[0]);	\
    PyList_Append(lst, arr);						\
  }

static int
LZWEncode(TIFF* tif, uint8* bp, tmsize_t cc/*, uint16 s*/
	  ,PyObject* lst)
{
	register LZWCodecState *sp = EncoderState(tif);
	register long fcode;
	register hash_t *hp;
	register int h, c;
	hcode_t ent;
	long disp;
	long incount, outcount, checkpoint;
	long nextdata, nextbits;
	int free_ent, maxcode, nbits;
	uint8* op;
	uint8* limit;

	//(void) s;
	if (sp == NULL)
		return (0);

        assert(sp->enc_hashtab != NULL);

	/*
	 * Load local state.
	 */
	incount = sp->enc_incount;
	outcount = sp->enc_outcount;
	checkpoint = sp->enc_checkpoint;
	nextdata = sp->lzw_nextdata;
	nextbits = sp->lzw_nextbits;
	free_ent = sp->lzw_free_ent;
	maxcode = sp->lzw_maxcode;
	nbits = sp->lzw_nbits;
	op = tif->tif_rawcp;
	limit = sp->enc_rawlimit;
	ent = sp->enc_oldcode;

	if (ent == (hcode_t) -1 && cc > 0) {
		/*
		 * NB: This is safe because it can only happen
		 *     at the start of a strip where we know there
		 *     is space in the data buffer.
		 */
		PutNextCode(op, CODE_CLEAR);
		ent = *bp++; cc--; incount++;
	}
	while (cc > 0) {
		c = *bp++; cc--; incount++;
		fcode = ((long)c << BITS_MAX) + ent;
		h = (c << HSHIFT) ^ ent;	/* xor hashing */
#ifdef _WINDOWS
		/*
		 * Check hash index for an overflow.
		 */
		if (h >= HSIZE)
			h -= HSIZE;
#endif
		hp = &sp->enc_hashtab[h];
		if (hp->hash == fcode) {
			ent = hp->code;
			continue;
		}
		if (hp->hash >= 0) {
			/*
			 * Primary hash failed, check secondary hash.
			 */
			disp = HSIZE - h;
			if (h == 0)
				disp = 1;
			do {
				/*
				 * Avoid pointer arithmetic 'cuz of
				 * wraparound problems with segments.
				 */
				if ((h -= disp) < 0)
					h += HSIZE;
				hp = &sp->enc_hashtab[h];
				if (hp->hash == fcode) {
					ent = hp->code;
					goto hit;
				}
			} while (hp->hash >= 0);
		}
		/*
		 * New entry, emit code and add to table.
		 */
		/*
		 * Verify there is space in the buffer for the code
		 * and any potential Clear code that might be emitted
		 * below.  The value of limit is setup so that there
		 * are at least 4 bytes free--room for 2 codes.
		 */
		if (op > limit) {
		  tif->tif_rawcc = (tmsize_t)(op - tif->tif_rawdata);
		  //TIFFFlushData1(tif);
		  FLUSHDATA(lst, tif->tif_rawdata, tif->tif_rawcc);
		  op = tif->tif_rawdata;
		}
		PutNextCode(op, ent);
		ent = c;
		hp->code = free_ent++;
		hp->hash = fcode;
		if (free_ent == CODE_MAX-1) {
			/* table is full, emit clear code and reset */
			cl_hash(sp);
			sp->enc_ratio = 0;
			incount = 0;
			outcount = 0;
			free_ent = CODE_FIRST;
			PutNextCode(op, CODE_CLEAR);
			nbits = BITS_MIN;
			maxcode = MAXCODE(BITS_MIN);
		} else {
			/*
			 * If the next entry is going to be too big for
			 * the code size, then increase it, if possible.
			 */
			if (free_ent > maxcode) {
				nbits++;
				assert(nbits <= BITS_MAX);
				maxcode = (int) MAXCODE(nbits);
			} else if (incount >= checkpoint) {
				long rat;
				/*
				 * Check compression ratio and, if things seem
				 * to be slipping, clear the hash table and
				 * reset state.  The compression ratio is a
				 * 24+8-bit fractional number.
				 */
				checkpoint = incount+CHECK_GAP;
				CALCRATIO(sp, rat);
				if (rat <= sp->enc_ratio) {
					cl_hash(sp);
					sp->enc_ratio = 0;
					incount = 0;
					outcount = 0;
					free_ent = CODE_FIRST;
					PutNextCode(op, CODE_CLEAR);
					nbits = BITS_MIN;
					maxcode = MAXCODE(BITS_MIN);
				} else
					sp->enc_ratio = rat;
			}
		}
	hit:
		;
	}

	/*
	 * Restore global state.
	 */
	sp->enc_incount = incount;
	sp->enc_outcount = outcount;
	sp->enc_checkpoint = checkpoint;
	sp->enc_oldcode = ent;
	sp->lzw_nextdata = nextdata;
	sp->lzw_nextbits = nextbits;
	sp->lzw_free_ent = free_ent;
	sp->lzw_maxcode = maxcode;
	sp->lzw_nbits = nbits;
	tif->tif_rawcp = op;
	return (1);
}

/*
 * Finish off an encoded strip by flushing the last
 * string and tacking on an End Of Information code.
 */
static int
LZWPostEncode(TIFF* tif, PyObject* lst)
{
	register LZWCodecState *sp = EncoderState(tif);
	uint8* op = tif->tif_rawcp;
	long nextbits = sp->lzw_nextbits;
	long nextdata = sp->lzw_nextdata;
	long outcount = sp->enc_outcount;
	int nbits = sp->lzw_nbits;

	if (op > sp->enc_rawlimit) {
		tif->tif_rawcc = (tmsize_t)(op - tif->tif_rawdata);
		//TIFFFlushData1(tif);
		FLUSHDATA(lst, tif->tif_rawdata, tif->tif_rawcc);
		op = tif->tif_rawdata;
	}
	if (sp->enc_oldcode != (hcode_t) -1) {
		PutNextCode(op, sp->enc_oldcode);
		sp->enc_oldcode = (hcode_t) -1;
	}
	PutNextCode(op, CODE_EOI);
	if (nextbits > 0) 
		*op++ = (unsigned char)(nextdata << (8-nextbits));
	tif->tif_rawcc = (tmsize_t)(op - tif->tif_rawdata);
	FLUSHDATA(lst, tif->tif_rawdata, tif->tif_rawcc);
	return (1);
}

/*
 * Reset encoding hash table.
 */
static void
cl_hash(LZWCodecState* sp)
{
	register hash_t *hp = &sp->enc_hashtab[HSIZE-1];
	register long i = HSIZE-8;

	do {
		i -= 8;
		hp[-7].hash = -1;
		hp[-6].hash = -1;
		hp[-5].hash = -1;
		hp[-4].hash = -1;
		hp[-3].hash = -1;
		hp[-2].hash = -1;
		hp[-1].hash = -1;
		hp[ 0].hash = -1;
		hp -= 8;
	} while (i >= 0);
	for (i += 8; i > 0; i--, hp--)
		hp->hash = -1;
}

static void
LZWCleanup(TIFF* tif)
{
  //(void)TIFFPredictorCleanup(tif);

	assert(tif->tif_data != 0);

	if (DecoderState(tif)->dec_codetab)
	  //_TIFFfree(DecoderState(tif)->dec_codetab);
	  free(DecoderState(tif)->dec_codetab);

	if (EncoderState(tif)->enc_hashtab)
	  //_TIFFfree(EncoderState(tif)->enc_hashtab);
	  free(EncoderState(tif)->enc_hashtab);

	//_TIFFfree(tif->tif_data);
	free(tif->tif_data);
	tif->tif_data = NULL;

	//_TIFFSetDefaultCompressionState(tif);
}

#if 0
int
TIFFInitLZW(TIFF* tif/*, int scheme*/)
{
  //static const char module[] = "TIFFInitLZW";
  //assert(scheme == COMPRESSION_LZW);
	/*
	 * Allocate state block so tag methods have storage to record values.
	 */
	//tif->tif_data = (uint8*) _TIFFmalloc(sizeof (LZWCodecState));
        tif->tif_data = (uint8*) malloc(sizeof (LZWCodecState));
	if (tif->tif_data == NULL)
		goto bad;
	DecoderState(tif)->dec_codetab = NULL;
	//DecoderState(tif)->dec_decode = NULL;
	EncoderState(tif)->enc_hashtab = NULL;
        //LZWState(tif)->rw_mode = tif->tif_mode;

	/*
	 * Install codec methods.
	 */
	/*
	tif->tif_fixuptags = LZWFixupTags; 
	tif->tif_setupdecode = LZWSetupDecode;
	tif->tif_predecode = LZWPreDecode;
	tif->tif_decoderow = LZWDecode;
	tif->tif_decodestrip = LZWDecode;
	tif->tif_decodetile = LZWDecode;
	tif->tif_setupencode = LZWSetupEncode;
	tif->tif_preencode = LZWPreEncode;
	tif->tif_postencode = LZWPostEncode;
	tif->tif_encoderow = LZWEncode;
	tif->tif_encodestrip = LZWEncode;
	tif->tif_encodetile = LZWEncode;
	tif->tif_cleanup = LZWCleanup;
	*/
	/*
	 * Setup predictor setup.
	 */
	//(void) TIFFPredictorInit(tif);
	return (1);
bad:
	//TIFFErrorExt(tif->tif_clientdata, module, 
	//	     "No space for LZW state block");
	return (0);
}
#endif /* if 0 */

static PyObject *py_decode(PyObject *self, PyObject *args, PyObject *kwds)
{
  PyObject* arr = NULL;
  PyObject* result = NULL;
  TIFF tif;
  static char* kwlist[] = {"arr","size",NULL};
  long occ;
  npy_intp dims[] = {0};
  PyArray_Dims newshape;
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "Oi", 
				   kwlist, &arr, dims))
    return NULL;
  if (!PyArray_Check(arr))
    {
      PyErr_SetString(PyExc_TypeError,"first argument must be array object");
      return NULL;
    }
  /* TIFFInitLZW */
  tif.tif_data = (uint8*) malloc(sizeof (LZWCodecState));
  DecoderState(&tif)->dec_codetab = NULL;
  //DecoderState(&tif)->dec_decode = NULL;
  EncoderState(&tif)->enc_hashtab = NULL;
  //LZWState(&tif)->rw_mode = tif->tif_mode;
  /* eof TIFFInitLZW */

  tif.tif_rawcp = tif.tif_rawdata = (uint8*)PyArray_DATA((PyArrayObject*)arr);
  tif.tif_rawcc = tif.tif_rawdatasize = PyArray_NBYTES((PyArrayObject*)arr);

  result = PyArray_EMPTY(1, dims, NPY_UBYTE, 0);
  if (result!=NULL)
    {

      LZWPreDecode(&tif);
      occ = LZWDecode(&tif, (uint8*)PyArray_DATA((PyArrayObject*)result), PyArray_NBYTES((PyArrayObject*)result));
      LZWCleanup(&tif);
      if (occ>0)
	{
	  dims[0] -= occ;
	  newshape.ptr = dims;
	  newshape.len = 1;
	  #if NPY_API_VERSION < 7
	  if (PyArray_Resize((PyArrayObject*)result, &newshape, 0, PyArray_CORDER)==NULL)
	  #else
	  if (PyArray_Resize((PyArrayObject*)result, &newshape, 0, NPY_CORDER)==NULL)
	  #endif
	    return NULL;
	}
    }
  return result;
}

static PyObject *py_encode(PyObject *self, PyObject *args, PyObject *kwds)
{
  PyObject* arr = NULL;
  PyObject* lst = PyList_New(0);
  PyObject* result = NULL;
  npy_intp dims[] = {0};
  int buffer_size;
  int i, j;

  TIFF tif;
  static char* kwlist[] = {"arr",NULL};
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "O", 
				   kwlist, &arr))
    return NULL;
  if (!PyArray_Check(arr))
    {
      PyErr_SetString(PyExc_TypeError,"first argument must be array object");
      return NULL;
    }

  /* TIFFInitLZW */
  tif.tif_data = (uint8*) malloc(sizeof (LZWCodecState));
  DecoderState(&tif)->dec_codetab = NULL;
  //DecoderState(&tif)->dec_decode = NULL;
  EncoderState(&tif)->enc_hashtab = NULL;
  //LZWState(&tif)->rw_mode = tif->tif_mode;
  /* eof TIFFInitLZW */

  // create buffer
  buffer_size = PyArray_NBYTES((PyArrayObject*)arr);
  if (buffer_size > (1<<20))
    buffer_size = (1<<20);
  tif.tif_rawcp = tif.tif_rawdata = (uint8*)malloc(buffer_size * sizeof(uint8));
  tif.tif_rawdatasize = buffer_size;

  // encode
  LZWPreEncode(&tif);
  LZWEncode(&tif, (uint8*)PyArray_DATA((PyArrayObject*)arr), PyArray_NBYTES((PyArrayObject*)arr), lst);
  LZWPostEncode(&tif, lst);

  // get result from buffer lst
  if (PyList_GET_SIZE(lst)==1)
    {
      result = PyList_GET_ITEM(lst, 0);
      Py_INCREF(result);
    }
  else
    {
      dims[0] = 0;
      for (i=0; i<PyList_GET_SIZE(lst); ++i)
	dims[0] += PyArray_NBYTES((PyArrayObject*)PyList_GET_ITEM(lst, i));
      result = PyArray_EMPTY(1, dims, NPY_UBYTE, 0);
      for (i=0, j=0; i<PyList_GET_SIZE(lst); ++i)
	{
	  PyObject* item = PyList_GET_ITEM(lst, i);
	  memcpy((char*)PyArray_DATA((PyArrayObject*)result) + j, PyArray_DATA((PyArrayObject*)item), PyArray_NBYTES((PyArrayObject*)item));
	  j += PyArray_NBYTES((PyArrayObject*)item);
	}
    }

  // cleanup
  LZWCleanup(&tif);
  free(tif.tif_rawdata);
  Py_DECREF(lst);

  return result;
}


static PyMethodDef module_methods[] = {
  {"encode", (PyCFunction)py_encode, METH_VARARGS|METH_KEYWORDS, "encode(array) - return LZW encoded array"},
  {"decode", (PyCFunction)py_decode, METH_VARARGS|METH_KEYWORDS, "decode(array, size) - return LZW decoded array of size (or less)"},
  {NULL}  /* Sentinel */
};

#ifdef IS_PY3K
static PyModuleDef moduledef = {
  PyModuleDef_HEAD_INIT, "tif_lzw", 0, -1, module_methods,
};
PyMODINIT_FUNC
PyInit_tif_lzw(void)
#else
PyMODINIT_FUNC
inittif_lzw(void)
#endif
{
  PyObject* m = NULL;
  import_array();
  if (PyErr_Occurred())
    {
      PyErr_SetString(PyExc_ImportError, "can't initialize module tif_lzw (failed to import numpy)"); 
      return NULL;
    }
#ifdef IS_PY3K
  m = PyModule_Create(&moduledef);
  if (m == NULL)
    return NULL;
#else
  m = Py_InitModule3("tif_lzw", module_methods, "");
  if (m == NULL)
    return;
#endif
  //  m = Py_InitModule3("tif_lzw", module_methods, "");

#ifdef IS_PY3K
  return m;
#endif
}


/*
 * Copyright (c) 1985, 1986 The Regents of the University of California.
 * All rights reserved.
 *
 * This code is derived from software contributed to Berkeley by
 * James A. Woods, derived from original work by Spencer Thomas
 * and Joseph Orost.
 *
 * Redistribution and use in source and binary forms are permitted
 * provided that the above copyright notice and this paragraph are
 * duplicated in all such forms and that any documentation,
 * advertising materials, and other materials related to such
 * distribution and use acknowledge that the software was developed
 * by the University of California, Berkeley.  The name of the
 * University may not be used to endorse or promote products derived
 * from this software without specific prior written permission.
 * THIS SOFTWARE IS PROVIDED ``AS IS'' AND WITHOUT ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, WITHOUT LIMITATION, THE IMPLIED
 * WARRANTIES OF MERCHANTIBILITY AND FITNESS FOR A PARTICULAR PURPOSE.
 */
//#endif /* LZW_SUPPORT */

/* vim: set ts=8 sts=8 sw=8 noet: */
