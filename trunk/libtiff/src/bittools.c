#include <Python.h>
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#define PY_ARRAY_UNIQUE_SYMBOL PyArray_API
#include "numpy/arrayobject.h"

#ifndef PyMODINIT_FUNC  /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

#define CHAR_BITS 8
#define CHAR_BITS_EXP 3

/* i/8 == i>>3 */
#define BITS(bytes)  (((unsigned long)(bytes)) << CHAR_BITS_EXP)
#define BYTES(bits)  (((bits) == 0) ? 0 : ((((bits) - 1) >> CHAR_BITS_EXP) + 1))
#define NBYTES(bits)  ((bits) >> CHAR_BITS_EXP)
#define BITMASK(i,width)  (((unsigned long) 1) << (((i))%(width)))
#define DATAPTR(data, i) ((char*)(data) + ((i)>>CHAR_BITS_EXP))
#define DATA(data, i) (*DATAPTR((data),(i)))
#define GETBIT(value, i, width) ((value & BITMASK((i),(width))) ? 1 : 0)
#define ARRGETBIT(arr, i) ((DATA(PyArray_DATA((PyArrayObject*)arr), (i)) & BITMASK((i),CHAR_BITS)) ? 1 : 0)

static PyObject *getbit(PyObject *self, PyObject *args, PyObject *kwds)
{
  PyObject* arr = NULL;
  char bit = 0;
  Py_ssize_t index = 0;
  static char* kwlist[] = {"array", "index", NULL};
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "|On:getbit", 
				   kwlist, &arr, &index))
    return NULL;

  if (!PyArray_Check(arr))
    {
      PyErr_SetString(PyExc_TypeError,"first argument must be array object");
      return NULL;
    }
  if (index >= BITS(PyArray_NBYTES((PyArrayObject*)arr)))
    {
      PyErr_SetString(PyExc_IndexError,"bit index out of range");
      return NULL;
    }
  bit = ARRGETBIT(arr, index);
  return Py_BuildValue("b",bit);
}

static PyObject *setbit(PyObject *self, PyObject *args, PyObject *kwds)
{
  PyObject* arr = NULL;
  char bit = 0, opt=0;
  Py_ssize_t index = 0;
  static char* kwlist[] = {"array", "index", "bit", "opt", NULL};
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "|Onbb:setbit", 
				   kwlist, &arr, &index, &bit, &opt))
    return NULL;
  if (!opt)
    {
      if (!PyArray_Check(arr))
	{
	  PyErr_SetString(PyExc_TypeError,"first argument must be array object");
	  return NULL;
	}
      if (NBYTES(index) >= PyArray_NBYTES((PyArrayObject*)arr))
	{
	  PyErr_SetString(PyExc_IndexError,"bit index out of range");
	  return NULL;
	}
    }
  if (bit)
    DATA(PyArray_DATA((PyArrayObject*)arr), index) |= BITMASK(index, CHAR_BITS);
  else
    DATA(PyArray_DATA((PyArrayObject*)arr), index) &= ~BITMASK(index, CHAR_BITS);
  Py_INCREF(Py_None);
  return Py_None;
}

static PyObject *getword(PyObject *self, PyObject *args, PyObject *kwds)
{
  PyObject* arr = NULL;
  Py_ssize_t index = 0;
  Py_ssize_t width = 0, i;
  static char* kwlist[] = {"array", "index", "width", NULL};
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "|Onn:getword", 
				   kwlist, &arr, &index, &width))
    return NULL;
  if (!PyArray_Check(arr))
    {
      PyErr_SetString(PyExc_TypeError,"first argument must be array object");
      return NULL;
    }
  if (((index+width-1) >= BITS(PyArray_NBYTES((PyArrayObject*)arr))) || (width<0))
    {
      PyErr_SetString(PyExc_IndexError,"bit index out of range");
      return NULL;
    }
  
  // fast code, at least 3x
  if (width<=32)
    {
      npy_uint32 x = *((npy_uint64*)DATAPTR(PyArray_DATA((PyArrayObject*)arr), index)) >> (index % CHAR_BITS);
      return Py_BuildValue("kn",x & (NPY_MAX_UINT32>>(32-width)), index+width);
    }
  // generic code
  if (width<=64)
    {
      npy_uint64 word = 0;
      for (i=0; i<width; ++i)
	if (ARRGETBIT(arr, index + i))
	    word |= BITMASK(i, width);
	else
	    word &= ~BITMASK(i, width);

      return Py_BuildValue("kn",word,index+width);
    }
  PyErr_SetString(PyExc_ValueError,"bit width must not be larger than 64");
  return NULL;
}

static PyObject *setword(PyObject *self, PyObject *args, PyObject *kwds)
{
  PyObject* arr = NULL;
  Py_ssize_t index = 0;
  Py_ssize_t width = 0, i, value_width=sizeof(npy_uint64)*CHAR_BITS;
  npy_uint64 value = 0;
  char opt = 0;
  static char* kwlist[] = {"array", "index", "width", "value", "opt", NULL};
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "|Onnkb:setword", 
				   kwlist, &arr, &index, &width, &value, &opt))
    return NULL;
  if (!opt)
    {
      if (!PyArray_Check(arr))
	{
	  PyErr_SetString(PyExc_TypeError,"first argument must be array object");
	  return NULL;
	}
      if ((index+width-1) >= BITS(PyArray_NBYTES((PyArrayObject*)arr)) || width<0)
	{
	  printf("index,width,nbits=%d,%d,%d\n", index, width, BITS(PyArray_NBYTES((PyArrayObject*)arr)));
	  PyErr_SetString(PyExc_IndexError,"bit index out of range");
	  return NULL;
	}
      if (width>64)
	{
	  PyErr_SetString(PyExc_ValueError,"bit width must not be larger than 64");
	  return NULL;
	}
    }
  for (i=0; i<width; ++i)
    if ((i<value_width) && (GETBIT(value, i, value_width)))
      DATA(PyArray_DATA((PyArrayObject*)arr), index+i) |= BITMASK(index+i, CHAR_BITS);
    else
      DATA(PyArray_DATA((PyArrayObject*)arr), index+i) &= ~BITMASK(index+i, CHAR_BITS);

  return Py_BuildValue("n",index + width);
  /*
  Py_INCREF(Py_None);
  return Py_None;
  */
}

static PyMethodDef module_methods[] = {
  {"getbit", (PyCFunction)getbit, METH_VARARGS|METH_KEYWORDS, "Get bit value of an array at bit index."},
  {"setbit", (PyCFunction)setbit, METH_VARARGS|METH_KEYWORDS, "Set bit value of an array at bit index."},
  {"getword", (PyCFunction)getword, METH_VARARGS|METH_KEYWORDS, "getword(array, bitindex, wordwidth) - get word value from an array at bitindex with bitwidth."},
  {"setword", (PyCFunction)setword, METH_VARARGS|METH_KEYWORDS, "setword(array, bitindex, wordwidth, word) - set word value to an array at bitindex with bitwidth."},
  {NULL}  /* Sentinel */
};

PyMODINIT_FUNC
initbittools(void) 
{
  PyObject* m = NULL;
  import_array();
  if (PyErr_Occurred())
    {
      PyErr_SetString(PyExc_ImportError, "can't initialize module bittools (failed to import numpy)"); 
      return;
    }
  m = Py_InitModule3("bittools", module_methods, "");
}
