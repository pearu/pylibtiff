#include <Python.h>
#define PY_ARRAY_UNIQUE_SYMBOL PyArray_API
#include "numpy/arrayobject.h"

#ifndef PyMODINIT_FUNC  /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

/* i/8 == i>>3 */
#define BITS(bytes)  ((((npy_intp) (bytes)) << 3)
#define BYTES(bits)  (((bits) == 0) ? 0 : ((((bits) - 1) >> 3) + 1))
#define NBYTES(bits)  ((bits) >> 3)
#define BITMASK(i,width)  (((char) 1) << ((i)%(width)))
#define DATAPTR(data, i) ((char*)(data) + ((i)>>3))
#define DATA(data, i) (*DATAPTR((data),(i)))
#define GETBIT(value, i, width) ((value & BITMASK((i),width)) ? 1 : 0)
#define ARRGETBIT(arr, i) ((DATA(PyArray_DATA(arr), (i)) & BITMASK((i),8)) ? 1 : 0)

static PyObject *getbit(PyObject *self, PyObject *args)
{
  PyObject* arr = NULL;
  char bit = 0;
  npy_uintp index = 0;

  if (!PyArg_ParseTuple(args, "Ok", &arr, &index))
    return NULL;
  if (!PyArray_Check(arr))
    {
      PyErr_SetString(PyExc_TypeError,"first argument must be array object");
      return NULL;
    }
  if (NBYTES(index) >= PyArray_NBYTES(arr))
    {
      PyErr_SetString(PyExc_IndexError,"bit index out of range");
      return NULL;
    }
  bit = ARRGETBIT(arr, index);
  return Py_BuildValue("b",bit);
}

static PyObject *setbit(PyObject *self, PyObject *args)
{
  PyObject* arr = NULL;
  char bit = 0;
  npy_uintp index = 0;
  if (!PyArg_ParseTuple(args, "Okb", &arr, &index, &bit))
    return NULL;
  if (!PyArray_Check(arr))
    {
      PyErr_SetString(PyExc_TypeError,"first argument must be array object");
      return NULL;
    }
  if (NBYTES(index) >= PyArray_NBYTES(arr))
    {
      PyErr_SetString(PyExc_IndexError,"bit index out of range");
      return NULL;
    }
  if (bit)
    DATA(PyArray_DATA(arr), index) |= BITMASK(index, 8);
  else
    DATA(PyArray_DATA(arr), index) &= ~BITMASK(index, 8);
  Py_INCREF(Py_None);
  return Py_None;
}

static PyObject *getword(PyObject *self, PyObject *args)
{
  PyObject* arr = NULL;
  npy_uintp index = 0;
  char width = 0, i;

  arr = PyTuple_GET_ITEM(args, 0);
  index = PyLong_AsUnsignedLongMask(PyTuple_GET_ITEM(args, 1));
  width = PyLong_AsUnsignedLongMask(PyTuple_GET_ITEM(args, 2));
  /*
  if (!PyArg_ParseTuple(args, "Okb", &arr, &index, &width))
    return NULL;
  if (!PyArray_Check(arr))
    {
      PyErr_SetString(PyExc_TypeError,"first argument must be array object");
      return NULL;
    }
  if (NBYTES(index+width-1) >= PyArray_NBYTES(arr))
    {
      PyErr_SetString(PyExc_IndexError,"bit index out of range");
      return NULL;
    }
  */
  
  if (width<=32)
    {
      npy_uint32 x = *((npy_uint64*)DATAPTR(PyArray_DATA(arr), index)) >> (index % 8);
      return Py_BuildValue("I",x & (NPY_MAX_UINT32>>(32-width)));
    }
  
  // generic code
  if (width<=64)
    {
      npy_uint64 word = 0;
      for (i=index; i<index+width; ++i)
	if (ARRGETBIT(arr, i))
	  word |= BITMASK(i, width);
	else
	  word &= ~BITMASK(i, width);
      return Py_BuildValue("k",word);
    }
  // todo: implement support for widths>64
  return NULL;
}

static PyObject *setword(PyObject *self, PyObject *args)
{
  PyObject* arr = NULL;
  npy_uintp index = 0;
  char width = 0, i;
  npy_int32 value = 0;
  arr = PyTuple_GET_ITEM(args, 0);
  index = PyLong_AsUnsignedLongMask(PyTuple_GET_ITEM(args, 1));
  width = PyLong_AsUnsignedLongMask(PyTuple_GET_ITEM(args, 2));
  value = PyLong_AsUnsignedLongMask(PyTuple_GET_ITEM(args, 3));

  for (i=0; i<width; ++i)
    if (GETBIT(value, i, 32))
      DATA(PyArray_DATA(arr), index+i) |= BITMASK(index+i, 8);
    else
      DATA(PyArray_DATA(arr), index+i) &= ~BITMASK(index+i, 8);

  Py_INCREF(Py_None);
  return Py_None;
}

static PyMethodDef module_methods[] = {
  {"getbit", getbit, METH_VARARGS, "Get bit value of an array at bit index."},
  {"setbit", setbit, METH_VARARGS, "Set bit value of an array at bit index."},
  {"getword", getword, METH_VARARGS, "getword(array, bitindex, wordwidth) - get word value from an array at bitindex with bitwidth."},
  {"setword", setword, METH_VARARGS, "setword(array, bitindex, wordwidth, word) - set word value to an array at bitindex with bitwidth."},
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
