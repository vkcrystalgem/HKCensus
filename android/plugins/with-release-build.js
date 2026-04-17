const { withAppBuildGradle } = require("@expo/config-plugins");

function replaceOrThrow(contents, searchValue, replaceValue, label) {
  if (!contents.includes(searchValue)) {
    throw new Error(`with-release-build: could not find ${label}`);
  }
  return contents.replace(searchValue, replaceValue);
}

function replaceIfNeeded(contents, searchValue, replaceValue, alreadyAppliedMarker, label) {
  if (contents.includes(alreadyAppliedMarker)) {
    return contents;
  }
  return replaceOrThrow(contents, searchValue, replaceValue, label);
}

module.exports = function withReleaseBuild(config) {
  return withAppBuildGradle(config, (config) => {
    if (config.modResults.language !== "groovy") {
      throw new Error("with-release-build only supports Groovy build.gradle files");
    }

    let contents = config.modResults.contents;

    const projectRootLine = "def projectRoot = rootDir.getAbsoluteFile().getParentFile().getAbsolutePath()";
    const releaseHelpers = `${projectRootLine}

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

def readDebugValue = { String key ->
    def qualifiedKey = "DEBUG_\${key}"
    def envValue = System.getenv("HKCENSUS_\${qualifiedKey}")
    if (envValue != null && !envValue.trim().isEmpty()) {
        return envValue.trim()
    }
    def propValue = releaseProps.getProperty(qualifiedKey)
    return (propValue != null && !propValue.trim().isEmpty()) ? propValue.trim() : null
}

def resolveReleaseFile = { String value ->
    if (value == null || value.trim().isEmpty()) {
        return null
    }
    def direct = file(value)
    return direct.isAbsolute() ? direct : new File(projectRoot, value)
}

def wantsReleaseBuild = gradle.startParameter.taskNames.any { task ->
    def normalized = task.toLowerCase()
    normalized.contains("release") || normalized.contains("publish")
}

def resolvedVersionCode = Integer.parseInt(readReleaseValue("VERSION_CODE") ?: "1")
def resolvedVersionName = readReleaseValue("VERSION_NAME") ?: "1.0.0"`;

    contents = replaceIfNeeded(
      contents,
      projectRootLine,
      releaseHelpers,
      "def resolvedVersionCode = Integer.parseInt(readReleaseValue(\"VERSION_CODE\") ?: \"1\")",
      "projectRoot definition"
    );
    if (!contents.includes("def readDebugValue = { String key ->")) {
      const releaseHelperPattern = /(def readReleaseValue = \{ String key ->[\s\S]*?return \(propValue != null && !propValue.trim\(\).isEmpty\(\)\) \? propValue.trim\(\) : null\s*\})/;
      if (!releaseHelperPattern.test(contents)) {
        throw new Error("with-release-build: could not find readReleaseValue");
      }
      const debugHelper = `def readDebugValue = { String key ->
    def qualifiedKey = "DEBUG_\${key}"
    def envValue = System.getenv("HKCENSUS_\${qualifiedKey}")
    if (envValue != null && !envValue.trim().isEmpty()) {
        return envValue.trim()
    }
    def propValue = releaseProps.getProperty(qualifiedKey)
    return (propValue != null && !propValue.trim().isEmpty()) ? propValue.trim() : null
}`;
      contents = contents.replace(releaseHelperPattern, `$1\n\n${debugHelper}`);
    }
    contents = replaceIfNeeded(
      contents,
      "        versionCode 1",
      "        versionCode resolvedVersionCode",
      "        versionCode resolvedVersionCode",
      "versionCode"
    );
    contents = replaceIfNeeded(
      contents,
      '        versionName "1.0.0"',
      "        versionName resolvedVersionName",
      "        versionName resolvedVersionName",
      "versionName"
    );

    const signingBlock = `    signingConfigs {
        debug {
            storeFile file('debug.keystore')
            storePassword 'android'
            keyAlias 'androiddebugkey'
            keyPassword 'android'
        }
    }`;

    const releaseSigningBlock = `    signingConfigs {
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
    }`;
    if (!contents.includes('            def keystoreFile = readDebugValue("KEYSTORE_FILE")')) {
      const signingPattern = /    signingConfigs\s*\{[\s\S]*?    }\s*    buildTypes\s*\{/;
      if (!signingPattern.test(contents)) {
        throw new Error("with-release-build: could not find signingConfigs");
      }
      contents = contents.replace(signingPattern, `${releaseSigningBlock}\n    buildTypes {`);
    }

    const releaseBuildType = `        release {
            // Caution! In production, you need to generate your own keystore file.
            // see https://reactnative.dev/docs/signed-apk-android.
            signingConfig signingConfigs.debug
            shrinkResources (findProperty('android.enableShrinkResourcesInReleaseBuilds')?.toBoolean() ?: false)
            minifyEnabled enableProguardInReleaseBuilds
            proguardFiles getDefaultProguardFile("proguard-android.txt"), "proguard-rules.pro"
            crunchPngs (findProperty('android.enablePngCrunchInReleaseBuilds')?.toBoolean() ?: true)
        }`;

    const hardenedReleaseBuildType = `        release {
            if (signingConfigs.release.storeFile != null) {
                signingConfig signingConfigs.release
            } else if (wantsReleaseBuild) {
                throw new GradleException("Missing release signing configuration. Provide HKCENSUS_KEYSTORE_FILE, HKCENSUS_KEYSTORE_PASSWORD, HKCENSUS_KEY_ALIAS, and HKCENSUS_KEY_PASSWORD, or create android/release.properties.")
            }
            shrinkResources (findProperty('android.enableShrinkResourcesInReleaseBuilds')?.toBoolean() ?: false)
            minifyEnabled enableProguardInReleaseBuilds
            proguardFiles getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro"
            crunchPngs (findProperty('android.enablePngCrunchInReleaseBuilds')?.toBoolean() ?: true)
        }`;
    contents = replaceIfNeeded(
      contents,
      releaseBuildType,
      hardenedReleaseBuildType,
      '                throw new GradleException("Missing release signing configuration. Provide HKCENSUS_KEYSTORE_FILE, HKCENSUS_KEYSTORE_PASSWORD, HKCENSUS_KEY_ALIAS, and HKCENSUS_KEY_PASSWORD, or create android/release.properties.")',
      "release buildType"
    );

    config.modResults.contents = contents;
    return config;
  });
};
