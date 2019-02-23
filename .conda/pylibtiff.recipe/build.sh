cd $RECIPE_DIR/../ || exit 1

pip install .
pytest -v libtiff/
