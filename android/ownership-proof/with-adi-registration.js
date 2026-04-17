const fs = require("fs");
const path = require("path");
const { withDangerousMod } = require("@expo/config-plugins");

module.exports = function withAdiRegistration(config) {
  return withDangerousMod(config, [
    "android",
    async (config) => {
      const registrationFile = process.env.HKCENSUS_ADI_REGISTRATION_FILE;
      if (!registrationFile) {
        return config;
      }

      const sourceFile = path.resolve(registrationFile);
      if (!fs.existsSync(sourceFile)) {
        throw new Error(`with-adi-registration: missing registration file: ${sourceFile}`);
      }

      const targetDir = path.join(
        config.modRequest.projectRoot,
        "android",
        "app",
        "src",
        "main",
        "assets"
      );
      await fs.promises.mkdir(targetDir, { recursive: true });
      await fs.promises.copyFile(sourceFile, path.join(targetDir, "adi-registration.properties"));
      return config;
    },
  ]);
};
