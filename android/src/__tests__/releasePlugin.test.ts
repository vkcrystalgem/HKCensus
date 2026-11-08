const { transformBuildGradle } = require("../../plugins/with-release-build");

// Relevant sections from Expo SDK 54's Android template, with a non-default app version.
const template = `def projectRoot = rootDir.getAbsoluteFile().getParentFile().getAbsolutePath()
android {
    defaultConfig {
        versionCode 42
        versionName "3.2.1"
    }
    signingConfigs {
        debug {
            storeFile file('debug.keystore')
            storePassword 'android'
            keyAlias 'androiddebugkey'
            keyPassword 'android'
        }
    }
    buildTypes {
        debug {
            signingConfig signingConfigs.debug
        }
        release {
            // Caution! In production, you need to generate your own keystore file.
            // see https://reactnative.dev/docs/signed-apk-android.
            signingConfig signingConfigs.debug
            def enableShrinkResources = findProperty('android.enableShrinkResourcesInReleaseBuilds') ?: 'false'
            shrinkResources enableShrinkResources.toBoolean()
            minifyEnabled enableMinifyInReleaseBuilds
            proguardFiles getDefaultProguardFile("proguard-android.txt"), "proguard-rules.pro"
            def enablePngCrunchInRelease = findProperty('android.enablePngCrunchInReleaseBuilds') ?: 'true'
            crunchPngs enablePngCrunchInRelease.toBoolean()
        }
    }
}`;

const config = { version: "1.0.1", android: { versionCode: 2 } };

describe("release signing prebuild plugin", () => {
  it("handles SDK 54 template changes and arbitrary source versions without losing build options", () => {
    const result = transformBuildGradle(template, config);
    expect(result).toContain('readReleaseValue("VERSION_CODE") ?: \'2\'');
    expect(result).toContain('readReleaseValue("VERSION_NAME") ?: \'1.0.1\'');
    expect(result).toContain("versionCode resolvedVersionCode");
    expect(result).toContain("versionName resolvedVersionName");
    expect(result).toContain("signingConfig signingConfigs.release");
    expect(result).toContain("else if (wantsReleaseBuild)");
    expect(result).toContain("minifyEnabled enableMinifyInReleaseBuilds");
    expect(result).toContain("shrinkResources enableShrinkResources.toBoolean()");
    expect(result.match(/signingConfig signingConfigs.debug/g)).toHaveLength(1);
  });

  it("is stable on repeated prebuilds and refreshes fallback versions from app config", () => {
    const first = transformBuildGradle(template, config);
    expect(transformBuildGradle(first, config)).toBe(first);
    const next = transformBuildGradle(first, { version: "1.0.2", android: { versionCode: 3 } });
    expect(next).toContain('readReleaseValue("VERSION_CODE") ?: \'3\'');
    expect(next).toContain('readReleaseValue("VERSION_NAME") ?: \'1.0.2\'');
    expect(next.match(/def releaseProps = new Properties/g)).toHaveLength(1);
  });

  it("fails when the release signing template cannot be recognized", () => {
    expect(() => transformBuildGradle(template.replace(
      /release \{[\s\S]*?signingConfig signingConfigs.debug/, "release { signingConfig customSigner"
    ), config)).toThrow("release signing declaration");
  });
});
