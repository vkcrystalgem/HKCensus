const { withAppBuildGradle } = require("@expo/config-plugins");

const HELPER_START = "// HK Census release helpers";
const PROJECT_ROOT = "def projectRoot = rootDir.getAbsoluteFile().getParentFile().getAbsolutePath()";

function replaceRequired(contents, pattern, replacement, label) {
  if (!pattern.test(contents)) {
    throw new Error(`with-release-build: could not find ${label}`);
  }
  return contents.replace(pattern, () => replacement);
}

function groovyLiteral(value) {
  return `'${String(value).replace(/\\/g, "\\\\").replace(/'/g, "\\'")}'`;
}

function transformBuildGradle(contents, config) {
  const versionCode = config.android?.versionCode ?? 1;
  if (!Number.isInteger(versionCode) || versionCode <= 0) {
    throw new Error("with-release-build: Android versionCode must be a positive integer");
  }
  const helpers = `${HELPER_START}
def releaseProps = new Properties()
def releasePropsFile = new File(projectRoot, "release.properties")
if (releasePropsFile.exists()) {
    releasePropsFile.withInputStream { releaseProps.load(it) }
}

def readReleaseValue = { String key ->
    def envValue = System.getenv("HKCENSUS_\${key}")
    if (envValue != null && !envValue.trim().isEmpty()) {
        return envValue.trim()
    }
    def propValue = releaseProps.getProperty(key)
    return (propValue != null && !propValue.trim().isEmpty()) ? propValue.trim() : null
}

def readDebugValue = { String key -> readReleaseValue("DEBUG_\${key}") }

def resolveReleaseFile = { String value ->
    def direct = new File(value)
    return direct.isAbsolute() ? direct : new File(projectRoot, value)
}

def wantsReleaseBuild = gradle.startParameter.taskNames.any { task ->
    def normalized = task.toLowerCase()
    normalized.contains("release") || normalized.contains("publish")
}

def resolvedVersionCode = Integer.parseInt(readReleaseValue("VERSION_CODE") ?: ${groovyLiteral(versionCode)})
def resolvedVersionName = readReleaseValue("VERSION_NAME") ?: ${groovyLiteral(config.version ?? "1.0.0")}
// End HK Census release helpers`;

  if (contents.includes(HELPER_START)) {
    contents = replaceRequired(contents, /\/\/ HK Census release helpers[\s\S]*?\/\/ End HK Census release helpers/, helpers, "release helpers");
  } else if (contents.includes("def readReleaseValue = {")) {
    contents = replaceRequired(contents,
      /def releaseProps = new Properties\(\)[\s\S]*?def resolvedVersionName = readReleaseValue\("VERSION_NAME"\) \?: "[^"]*"/,
      helpers, "legacy release helpers");
  } else {
    if (!contents.includes(PROJECT_ROOT)) {
      throw new Error("with-release-build: could not find projectRoot definition");
    }
    contents = contents.replace(PROJECT_ROOT, () => `${PROJECT_ROOT}\n\n${helpers}`);
  }

  contents = replaceRequired(contents, /^\s*versionCode\s+(?:\d+|resolvedVersionCode)\s*$/m,
    "        versionCode resolvedVersionCode", "versionCode");
  contents = replaceRequired(contents, /^\s*versionName\s+(?:"[^"]*"|'[^']*'|resolvedVersionName)\s*$/m,
    "        versionName resolvedVersionName", "versionName");

  const signingConfigs = `    signingConfigs {
        debug {
            def keystoreFile = readDebugValue("KEYSTORE_FILE")
            def keystorePassword = readDebugValue("KEYSTORE_PASSWORD")
            def keyAliasValue = readDebugValue("KEY_ALIAS")
            def keyPasswordValue = readDebugValue("KEY_PASSWORD")
            if (keystoreFile && keystorePassword && keyAliasValue && keyPasswordValue) {
                storeFile resolveReleaseFile(keystoreFile)
                storePassword keystorePassword
                keyAlias keyAliasValue
                keyPassword keyPasswordValue
            } else {
                storeFile file('debug.keystore')
                storePassword 'android'
                keyAlias 'androiddebugkey'
                keyPassword 'android'
            }
        }
        release {
            def keystoreFile = readReleaseValue("KEYSTORE_FILE")
            def keystorePassword = readReleaseValue("KEYSTORE_PASSWORD")
            def keyAliasValue = readReleaseValue("KEY_ALIAS")
            def keyPasswordValue = readReleaseValue("KEY_PASSWORD")
            if (keystoreFile && keystorePassword && keyAliasValue && keyPasswordValue) {
                storeFile resolveReleaseFile(keystoreFile)
                storePassword keystorePassword
                keyAlias keyAliasValue
                keyPassword keyPasswordValue
            }
        }
    }
    buildTypes {`;
  contents = replaceRequired(contents, /    signingConfigs\s*\{[\s\S]*?\n    }\s*\n    buildTypes\s*\{/,
    signingConfigs, "signingConfigs");

  // Keep the SDK's shrink/minify settings and replace only its release signing declaration.
  const releaseSigning = `        release {
            if (signingConfigs.release.storeFile != null) {
                signingConfig signingConfigs.release
            } else if (wantsReleaseBuild) {
                throw new GradleException("Missing release signing configuration. Provide HKCENSUS_KEYSTORE_FILE, HKCENSUS_KEYSTORE_PASSWORD, HKCENSUS_KEY_ALIAS, and HKCENSUS_KEY_PASSWORD, or create android/release.properties.")
            }`;
  if (!contents.includes("else if (wantsReleaseBuild)")) {
    contents = replaceRequired(contents,
      /        release\s*\{\s*(?:\/\/[^\n]*\n\s*)*signingConfig signingConfigs\.debug/,
      releaseSigning, "release signing declaration");
  }
  return contents;
}

module.exports = function withReleaseBuild(config) {
  return withAppBuildGradle(config, (modConfig) => {
    if (modConfig.modResults.language !== "groovy") {
      throw new Error("with-release-build only supports Groovy build.gradle files");
    }
    modConfig.modResults.contents = transformBuildGradle(modConfig.modResults.contents, modConfig);
    return modConfig;
  });
};

module.exports.transformBuildGradle = transformBuildGradle;
