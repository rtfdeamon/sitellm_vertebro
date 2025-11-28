const path = require("path");

module.exports = (env, argv) => {
  const isProd = argv.mode === "production";

  return {
    entry: "./src/index.ts",
    output: {
      filename: "voice-widget.js",
      path: path.resolve(__dirname, "dist"),
      library: {
        name: "VoiceWidget",
        type: "umd",
        export: "default",
      },
      globalObject: "this",
      clean: true,
    },
    resolve: {
      extensions: [".ts", ".tsx", ".js"],
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: "ts-loader",
          exclude: /node_modules/,
        },
        {
          test: /\.css$/i,
          use: ["style-loader", "css-loader"],
        },
      ],
    },
    devServer: {
      static: {
        directory: path.join(__dirname, "public"),
      },
      compress: true,
      port: 4100,
      hot: true,
    },
    devtool: isProd ? "source-map" : "eval-source-map",
  };
};

