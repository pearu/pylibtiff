# Releasing Pylibtiff

1. checkout master branch
2. pull from repo
3. run the unittests
4. Create a tag with the new version number, starting with a 'v', eg:

   ```
   git tag -a v<new version> -m "Version <new version>"
   ```

   For example if the previous tag was `v0.9.0` and the new release is a
   patch release, do:

   ```
   git tag -a v0.9.1 -m "Version 0.9.1"
   ```

   See [semver.org](http://semver.org/) on how to write a version number.


5. push changes to github `git push --follow-tags`
6. Verify github action unittests passed.
7. Create a "Release" on GitHub by going to
   https://github.com/pearu/pylibtiff/releases and clicking "Draft a new release".
   On the next page enter the newly created tag in the "Tag version" field,
   "Version X.Y.Z" in the "Release title" field, and record changes made in
   this release in the
   "Describe this release" box. Finally click "Publish release".
9. Verify the GitHub actions for deployment succeed and the release is on PyPI.
