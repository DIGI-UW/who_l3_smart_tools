import os
import re
import sys


class CQLSubsetGenerator:
    def __init__(
        self, parent_path, base_cql_dir, output_dir, elements_path, indicators_path
    ):
        self.parent_path = parent_path
        self.base_cql_dir = base_cql_dir
        self.output_dir = output_dir
        self.elements_path = elements_path
        self.indicators_path = indicators_path
        # Build indexes for quick lookup
        self.indicator_index = self.build_index(self.indicators_path)
        self.elements_index = self.build_index(self.elements_path)

    def read_file(self, file_path):
        with open(file_path, encoding="utf-8") as f:
            return f.read()

    def build_index(self, file_path):
        index = {}
        content = self.read_file(file_path)
        # Match definitions: assume pattern: define "DefinitionName":
        pattern = re.compile(
            r'(define\s+(?:"([^"]+)"|([a-zA-Z0-9_]+))\s*:)', re.IGNORECASE
        )
        matches = list(pattern.finditer(content))
        for idx, match in enumerate(matches):
            name = match.group(2) if match.group(2) else match.group(3)
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
            index[name.strip()] = content[start:end].strip()
        return index

    def get_header(self, file_path):
        header_lines = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if re.match(r"\s*define\s+", line, re.IGNORECASE):
                    break
                header_lines.append(line)
        return "".join(header_lines)

    def extract_references(self, content, prefix):
        # Extract definitions referenced like HIE."Name" or HE."Name"
        refs = set()
        pattern = re.compile(rf'\b{prefix}\.(?:"([^"]+)"|([a-zA-Z0-9_]+))')
        for m in pattern.finditer(content):
            ref = m.group(1) if m.group(1) else m.group(2)
            refs.add(ref.strip())
        return refs

    def resolve_dependencies(self, initial_refs, index, prefix):
        # Recursively add definitions from the provided index along with any intra-file references.
        resolved = {}
        pending = list(initial_refs)
        # Pattern for prefix references e.g. HIE."Ref"
        pattern_prefix = re.compile(rf'\b{prefix}\.(?:"([^"]+)"|([a-zA-Z0-9_]+))')
        # Pattern for intra-file quoted definitions (without prefix)
        pattern_intra = re.compile(r'"([^"]+)"')
        while pending:
            ref = pending.pop()
            if ref in resolved:
                continue
            if ref in index:
                definition = index[ref]
                resolved[ref] = definition
                # Look for further prefix-based references within this definition
                for m in pattern_prefix.finditer(definition):
                    nested = m.group(1) if m.group(1) else m.group(2)
                    if nested and nested.strip() not in resolved:
                        pending.append(nested.strip())
                # Additionally, look for intra-file dependencies: any quoted string that matches a definition name in the index
                for m in pattern_intra.finditer(definition):
                    nested_intra = m.group(1)
                    if (
                        nested_intra
                        and nested_intra.strip() in index
                        and nested_intra.strip() not in resolved
                    ):
                        pending.append(nested_intra.strip())
            else:
                print(
                    f"Warning: definition '{ref}' not found in index for prefix {prefix}",
                    file=sys.stderr,
                )
        return resolved

    def generate_subset(self):
        # Process the parent file (HIVIND20Logic.cql)
        parent_content = self.read_file(self.parent_path)

        # Extract initial references for IndicatorElements (HIE) and Elements (HE)
        indicator_elements_refs = self.extract_references(parent_content, "HIE")
        elements_refs = self.extract_references(parent_content, "HE")

        indicator_defs = self.resolve_dependencies(
            indicator_elements_refs, self.indicator_index, "HIE"
        )

        elements_defs = self.resolve_dependencies(
            elements_refs, self.elements_index, "HE"
        )

        # Indicator definitions might reference Elements using HE. so scan each indicator def:
        for def_text in list(indicator_defs.values()):
            extra = self.extract_references(def_text, "Elements")
            extra_defs = self.resolve_dependencies(
                extra, self.elements_index, "Elements"
            )
            elements_defs.update(extra_defs)

        # Build final subset content preserving headers
        indicator_header = self.get_header(self.indicators_path)
        elements_header = self.get_header(self.elements_path)
        indicator_subset = (
            indicator_header
            + "\n// ...subset definitions...\n"
            + "\n\n".join(indicator_defs.values())
        )
        elements_subset = (
            elements_header
            + "\n// ...subset definitions...\n"
            + "\n\n".join(elements_defs.values())
        )

        os.makedirs(self.output_dir, exist_ok=True)
        indicator_out = os.path.join(
            self.output_dir, os.path.basename(self.indicators_path)
        )
        with open(indicator_out, "w", encoding="utf-8") as f:
            f.write(indicator_subset)
        elements_out = os.path.join(
            self.output_dir, os.path.basename(self.elements_path)
        )
        with open(elements_out, "w", encoding="utf-8") as f:
            f.write(elements_subset)

    def run(self):
        self.generate_subset()


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: python cql_subset_generation.py <parent_cql> <base_cql_dir> <elements_cql> <indicators_cql>"
        )
        sys.exit(1)
    parent_file = sys.argv[1]
    base_cql_dir = sys.argv[2]
    elements_file = sys.argv[3]
    indicators_file = sys.argv[4]
    output_dir = os.path.join(base_cql_dir, "subsets")
    generator = CQLSubsetGenerator(
        parent_path=parent_file,
        base_cql_dir=base_cql_dir,
        output_dir=output_dir,
        elements_path=elements_file,
        indicators_path=indicators_file,
    )
    generator.run()
