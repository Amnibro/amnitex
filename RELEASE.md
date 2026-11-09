# Releasing AmniTeX

Everything runs on this machine. Do not use GitHub Actions or any other hosted build.

1. Edit the Helium fence in `atex_serve.gold`, then regenerate the Helium with `gold build atex_serve.gold` (set `GOLD_HC` and `GOLD_HC_LIB`). Do the same for `tests/atex_test.gold`.
2. Update the version in `atex_serve.gold` and every manifest. The test suite checks that they all agree.
3. Build through public Helium and run the tests:

   ```bash
   HELIUM=$PWD/.helium sh scripts/build-native.sh ./atex-bin
   HC_LIB=.helium/hc/lib .helium/build/hc build tests/atex_test.amni -o ./atex-test
   ./atex-test ./atex-bin .
   ```

4. Run `sh build.sh` to produce `dist/`.
5. Commit and push to `main`, then publish:

   ```bash
   gh release create vX.Y.Z -R Amnibro/amnitex --target main --title "..." --notes-file notes.md \
     dist/amnitex-helium.tar.gz dist/amnitex-linux-x64.tar.gz dist/amnitex.mcpb dist/install.sh dist/SHA256SUMS
   ```

6. Check both public install routes in a sandbox `HOME`: `curl -fsSL https://github.com/Amnibro/amnitex/releases/latest/download/install.sh | sh` and `curl -fsSL https://amni-scient.com/atex-install.sh | sh`.
