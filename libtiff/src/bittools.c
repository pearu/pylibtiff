#include <Python.h>
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#define PY_ARRAY_UNIQUE_SYMBOL bittools_PyArray_API
#include "numpy/arrayobject.h"

#define CHAR_BITS 8
#define CHAR_BITS_EXP 3

/* i/8 == i>>3 */
#define BITS(bytes)  (((npy_uint64)(bytes)) << CHAR_BITS_EXP)
#define BYTES(bits)  (((bits) == 0) ? 0 : ((((bits) - 1) >> CHAR_BITS_EXP) + 1))
#define BITMASK(i,width)  (((npy_uint64) 1) << (((i))%(width)))
#define BYTEMASK(i)  ((unsigned char)(1U << ((i) % CHAR_BITS)))
#define DATAPTR(data, i) ((unsigned char*)(data) + ((i)>>CHAR_BITS_EXP))
#define DATA(data, i) (*DATAPTR((data),(i)))
#define GETBIT(value, i, width) ((value & BITMASK((i),(width))) ? 1 : 0)
#define ARRGETBIT(arr, i) ((DATA(PyArray_DATA((PyArrayObject*)arr), (i)) & BYTEMASK(i)) ? 1 : 0)

/*
 * Check that the array data is a single contiguous segment (and writeable,
 * if requested) and that the bits [index, index+width) lie within it.
 */
static int check_bit_range(PyArrayObject* arr, Py_ssize_t index, Py_ssize_t width, int writeable)
{
  if (!PyArray_ISONESEGMENT(arr))
    {
      PyErr_SetString(PyExc_ValueError,"array must be contiguous");
      return -1;
    }
  if (writeable && PyArray_FailUnlessWriteable(arr, "array") < 0)
    return -1;
  if (index < 0 || width < 0
      || (npy_uint64)index + (npy_uint64)width > BITS(PyArray_NBYTES(arr)))
    {
      PyErr_SetString(PyExc_IndexError,"bit index out of range");
      return -1;
    }
  return 0;
}

static PyObject *getbit(PyObject *self, PyObject *args, PyObject *kwds)
{
  PyArrayObject* arr = NULL;
  char bit = 0;
  Py_ssize_t index = 0;
  static char* kwlist[] = {"array", "index", NULL};
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!|n:getbit",
				   kwlist, &PyArray_Type, &arr, &index))
    return NULL;
  if (check_bit_range(arr, index, 1, 0) < 0)
    return NULL;
  bit = ARRGETBIT(arr, index);
  return Py_BuildValue("b",bit);
}

static PyObject *setbit(PyObject *self, PyObject *args, PyObject *kwds)
{
  PyArrayObject* arr = NULL;
  char bit = 0, opt=0;
  Py_ssize_t index = 0;
  static char* kwlist[] = {"array", "index", "bit", "opt", NULL};
  /* opt is accepted for backwards compatibility but ignored:
     arguments are always checked. */
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!|nbb:setbit",
				   kwlist, &PyArray_Type, &arr, &index, &bit, &opt))
    return NULL;
  if (check_bit_range(arr, index, 1, 1) < 0)
    return NULL;
  if (bit)
    DATA(PyArray_DATA(arr), index) |= BYTEMASK(index);
  else
    DATA(PyArray_DATA(arr), index) &= (unsigned char)~BYTEMASK(index);
  Py_RETURN_NONE;
}

static PyObject *getword(PyObject *self, PyObject *args, PyObject *kwds)
{
  PyArrayObject* arr = NULL;
  Py_ssize_t index = 0;
  Py_ssize_t width = 0, i;
  static char* kwlist[] = {"array", "index", "width", NULL};
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!|nn:getword",
				   kwlist, &PyArray_Type, &arr, &index, &width))
    return NULL;
  if (width > 64)
    {
      PyErr_SetString(PyExc_ValueError,"bit width must not be larger than 64");
      return NULL;
    }
  if (check_bit_range(arr, index, width, 0) < 0)
    return NULL;
  if (width == 0)
    return Py_BuildValue("Kn", (unsigned long long)0, index);

  // fast code, at least 3x
  if (width<=32)
    {
      /* Assemble only the (at most 5) bytes holding the requested bits,
	 in little-endian order, so that nothing past the end of the
	 array is read and the result does not depend on host byte order. */
      const unsigned char* ptr = DATAPTR(PyArray_DATA(arr), index);
      Py_ssize_t shift = index % CHAR_BITS;
      Py_ssize_t k, nbytes = BYTES(shift + width);
      npy_uint64 x = 0;
      for (k=0; k<nbytes; ++k)
	x |= ((npy_uint64)ptr[k]) << (k * CHAR_BITS);
      x = (x >> shift) & ((((npy_uint64)1) << width) - 1);
      return Py_BuildValue("Kn", (unsigned long long)x, index+width);
    }
  // generic code
  {
    npy_uint64 word = 0;
    for (i=0; i<width; ++i)
      if (ARRGETBIT(arr, index + i))
	word |= BITMASK(i, width);
      else
	word &= ~BITMASK(i, width);

    return Py_BuildValue("Kn", (unsigned long long)word, index+width);
  }
}

static PyObject *setword(PyObject *self, PyObject *args, PyObject *kwds)
{
  PyArrayObject* arr = NULL;
  Py_ssize_t index = 0;
  Py_ssize_t width = 0, i, value_width=sizeof(npy_uint64)*CHAR_BITS;
  unsigned long long value = 0;
  char opt = 0;
  static char* kwlist[] = {"array", "index", "width", "value", "opt", NULL};
  /* opt is accepted for backwards compatibility but ignored:
     arguments are always checked. */
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!|nnKb:setword",
				   kwlist, &PyArray_Type, &arr, &index, &width, &value, &opt))
    return NULL;
  if (width > 64)
    {
      PyErr_SetString(PyExc_ValueError,"bit width must not be larger than 64");
      return NULL;
    }
  if (check_bit_range(arr, index, width, 1) < 0)
    return NULL;
  for (i=0; i<width; ++i)
    if (GETBIT(value, i, value_width))
      DATA(PyArray_DATA(arr), index+i) |= BYTEMASK(index+i);
    else
      DATA(PyArray_DATA(arr), index+i) &= (unsigned char)~BYTEMASK(index+i);

  return Py_BuildValue("n",index + width);
}

static PyMethodDef module_methods[] = {
  {"getbit", (PyCFunction)(void(*)(void))getbit, METH_VARARGS|METH_KEYWORDS, "Get bit value of an array at bit index."},
  {"setbit", (PyCFunction)(void(*)(void))setbit, METH_VARARGS|METH_KEYWORDS, "Set bit value of an array at bit index."},
  {"getword", (PyCFunction)(void(*)(void))getword, METH_VARARGS|METH_KEYWORDS, "getword(array, bitindex, wordwidth) - get word value from an array at bitindex with bitwidth."},
  {"setword", (PyCFunction)(void(*)(void))setword, METH_VARARGS|METH_KEYWORDS, "setword(array, bitindex, wordwidth, word) - set word value to an array at bitindex with bitwidth."},
  {NULL}  /* Sentinel */
};

static int
bittools_exec(PyObject *module)
{
  (void)module;
  import_array1(-1);
  return 0;
}

/*
 * The module keeps no mutable global state (the numpy C-API table is
 * only set during import), so it can run without the GIL.  numpy does
 * not support subinterpreters.
 */
static PyModuleDef_Slot module_slots[] = {
  {Py_mod_exec, (void*)bittools_exec},
#ifdef Py_mod_multiple_interpreters
  {Py_mod_multiple_interpreters, Py_MOD_MULTIPLE_INTERPRETERS_NOT_SUPPORTED},
#endif
#ifdef Py_mod_gil
  {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
  {0, NULL}
};

static PyModuleDef moduledef = {
  PyModuleDef_HEAD_INIT, "bittools", NULL, 0, module_methods, module_slots, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_bittools(void)
{
  return PyModuleDef_Init(&moduledef);
}
