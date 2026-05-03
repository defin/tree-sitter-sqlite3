// swift-tools-version:5.3
import PackageDescription

let package = Package(
    name: "TreeSitterSqlite3",
    products: [
        .library(name: "TreeSitterSqlite3", targets: ["TreeSitterSqlite3"]),
    ],
    dependencies: [],
    targets: [
        .target(
            name: "TreeSitterSqlite3",
            path: ".",
            exclude: [
                "Cargo.toml",
                "Makefile",
                "binding.gyp",
                "bindings/c",
                "bindings/go",
                "bindings/node",
                "bindings/python",
                "bindings/rust",
                "grammar.js",
                "package.json",
                "package-lock.json",
                "pyproject.toml",
                "setup.py",
                "test",
                "tree-sitter.json",
                "vendor",
            ],
            sources: [
                "src/parser.c",
                "src/scanner.c",
            ],
            resources: [
                .copy("queries"),
            ],
            publicHeadersPath: "bindings/swift",
            cSettings: [.headerSearchPath("src")]
        ),
    ]
)
