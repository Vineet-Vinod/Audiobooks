import re


class TTSNormalizationModel:
    """Rule-based text normalization for technical-book TTS input."""

    def __init__(self):
        self.replacements = DEFAULT_REPLACEMENTS
        self.first_use_expansions = DEFAULT_FIRST_USE_EXPANSIONS
        self.phrase_replacements = DEFAULT_PHRASE_REPLACEMENTS
        self.artifact_replacements = DEFAULT_ARTIFACT_REPLACEMENTS

    def normalize(self, text):
        text = self.fix_pdf_text_artifacts(text)
        text = self.normalize_punctuation(text)
        text = self.expand_phrases(text)
        text = self.rewrite_figures_tables_and_examples(text)
        text = self.rewrite_units(text)
        text = self.expand_first_use_acronyms(text)
        text = self.expand_replacements(text)
        text = self.rewrite_urls_and_paths(text)
        text = self.rewrite_symbols(text)
        text = self.clean_whitespace(text)
        return text

    def fix_pdf_text_artifacts(self, text):
        for source, target in self.artifact_replacements.items():
            text = text.replace(source, target)
        return text

    def normalize_punctuation(self, text):
        text = text.replace("[...]", "")
        text = text.replace("[\u2026]", "")
        text = text.replace("...", ",")
        text = text.replace("\u2026", ",")
        text = re.sub(r"(?<=[.!?])\s*\u2014\s*", " ", text)
        text = text.replace("\u2014", ", ")
        text = text.replace("extract\u2013transform\u2013load", "extract, transform, load")
        text = text.replace("extract\u2013load\u2013transform", "extract, load, transform")
        text = re.sub(r"(?<=\d)\u2013(?=\d)", " to ", text)
        text = text.replace("\u2013", ", ")
        text = text.replace("\u2010", "-")
        text = text.replace("\u2212", " minus ")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u2032", " prime")
        text = text.replace("\u00b0", " degrees ")
        text = text.replace("\u00b7", " times ")
        text = text.replace("\u221e", "infinity")
        text = text.replace("\u2264", " less than or equal to ")
        text = text.replace("\u2713", "yes")
        text = text.replace("\u2717", "no")
        text = text.replace("\u21d2", "returns")
        text = text.replace("• ", "")
        text = text.replace(" .", ".")
        text = text.replace(" ,", ",")
        return text

    def expand_phrases(self, text):
        for pattern, replacement in self.phrase_replacements:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def rewrite_figures_tables_and_examples(self, text):
        text = re.sub(
            r"\b(Figure|Table|Example)\s+(\d+)-(\d+)\b",
            r"\1 \2 point \3",
            text,
        )
        text = re.sub(r"\bChapter\s+(\d+)\b", r"Chapter \1", text)
        return text

    def rewrite_units(self, text):
        unit_replacements = {
            "KiB": "kibibytes",
            "KB": "kilobytes",
            "MB": "megabytes",
            "GB": "gigabytes",
            "TB": "terabytes",
            "PB": "petabytes",
            "ms": "milliseconds",
            "Gbps": "gigabits per second",
            "MB/s": "megabytes per second",
            "GB/s": "gigabytes per second",
            "Kb/s": "kilobits per second",
        }
        for unit, spoken in sorted(unit_replacements.items(), key=lambda item: -len(item[0])):
            text = re.sub(rf"\b(\d+(?:\.\d+)?)\s*{re.escape(unit)}\b", rf"\1 {spoken}", text)
        text = re.sub(r"\b(\d+(?:\.\d+)?)%", r"\1 percent", text)
        return text

    def expand_replacements(self, text):
        sorted_terms = sorted(self.replacements, key=len, reverse=True)
        term_pattern = "|".join(re.escape(term) for term in sorted_terms)

        text = re.sub(
            rf"\b({term_pattern})s\b",
            lambda match: f"{self.replacements[match.group(1)]}'s",
            text,
        )
        return re.sub(
            rf"\b({term_pattern})\b",
            lambda match: self.replacements[match.group(1)],
            text,
        )

    def expand_first_use_acronyms(self, text):
        for term in sorted(self.first_use_expansions, key=len, reverse=True):
            full_form, spoken_acronym = self.first_use_expansions[term]
            seen = f"{full_form}, or {spoken_acronym}" in text

            def replace(match):
                nonlocal seen
                if seen:
                    return spoken_acronym
                seen = True
                return f"{full_form}, or {spoken_acronym}"

            text = re.sub(rf"\b{re.escape(term)}\b", replace, text)
        return text

    def rewrite_symbols(self, text):
        symbol_replacements = (
            (r"->", " points to "),
            (r"=>", " returns "),
            (r"==", " equals "),
            (r"!=", " does not equal "),
            (r"<=", " less than or equal to "),
            (r">=", " greater than or equal to "),
            (r"\+/-|\+/\u2013", " plus or minus "),
            (r"(?<=\w)=(?=\w)", " equals "),
            (r"(?<=\s)=(?=\s)", " equals "),
            (r"(?<=\w)<(?=\w)", " less than "),
            (r"(?<=\w)>(?=\w)", " greater than "),
            (r"\b([A-Z])\s*/\s*([A-Z])\b", r"\1 slash \2"),
        )
        for pattern, replacement in symbol_replacements:
            text = re.sub(pattern, replacement, text)
        text = text.replace("&", " and ")
        text = text.replace("<", " less than ")
        text = text.replace(">", " greater than ")
        text = text.replace("=", " equals ")
        text = text.replace("+", " plus ")
        text = text.replace("%", " percent ")
        text = text.replace("|", " pipe ")
        text = text.replace("*", " star ")
        text = text.replace("#", " hash ")
        text = text.replace("@", " at ")
        text = text.replace("_", " underscore ")
        text = text.replace("/", " and ")
        return self.rewrite_hyphenated_words(text)

    def rewrite_hyphenated_words(self, text):
        while True:
            next_text = re.sub(r"\b([A-Za-z]+)-([A-Za-z]+)\b", r"\1 \2", text)
            if next_text == text:
                return text
            text = next_text

    def rewrite_urls_and_paths(self, text):
        text = re.sub(r"\bhttps?://", "", text)
        text = text.replace("www.", "W W W dot ")
        text = re.sub(r"(?<=\w)\.(?=\w)", " dot ", text)
        return text

    def clean_whitespace(self, text):
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r"([,.;:!?])([^\s\n])", r"\1 \2", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


DEFAULT_ARTIFACT_REPLACEMENTS = {
    "analysisfriendly": "analysis-friendly",
    "appendonly": "append-only",
    "columnoriented": "column-oriented",
    "higherlatency": "higher-latency",
    "higherlevel": "higher-level",
    "rowbased": "row-based",
    "serverside": "server-side",
    "singlethreaded": "single-threaded",
    "welldefined": "well-defined",
}


DEFAULT_PHRASE_REPLACEMENTS = (
    (
        r"\bonline transaction processing\s*\(OLTP\)",
        "online transaction processing, or O L T P",
    ),
    (
        r"\bonline analytical processing\s*\(OLAP\)",
        "online analytical processing, or O L A P",
    ),
    (
        r"\bhybrid transactional/analytical processing\s*\(HTAP\)",
        "hybrid transactional and analytical processing, or H T A P",
    ),
    (
        r"\bserializable snapshot isolation\s*\(SSI\)",
        "serializable snapshot isolation, or S S I",
    ),
    (
        r"\bmulti-version concurrency control\s*\(MVCC\)",
        "multi version concurrency control, or M V C C",
    ),
    (
        r"\bchange data capture\s*\(CDC\)",
        "change data capture, or C D C",
    ),
    (
        r"\bconflict-free replicated data types?\s*\(CRDTs?\)",
        "conflict free replicated data types, or C R D T's",
    ),
    (
        r"\blog-structured merge\s*\(LSM\)",
        "log structured merge, or L S M",
    ),
    (
        r"\blast writer wins\s*\(LWW\)",
        "last writer wins, or L W W",
    ),
    (
        r"\bwrite-ahead log\s*\(WAL\)",
        "write ahead log, or W A L",
    ),
    (
        r"\bextract(?:\s*[-\u2013]\s*|,?\s+)transform(?:\s*[-\u2013]\s*|,?\s+)load\s*\(ETL\)",
        "extract, transform, load, or E T L",
    ),
    (
        r"\bextract(?:\s*[-\u2013]\s*|,?\s+)load(?:\s*[-\u2013]\s*|,?\s+)transform\s*\(ELT\)",
        "extract, load, transform, or E L T",
    ),
    (
        r"\bmachine learning\s*\(ML\)/AI\b",
        "machine learning and artificial intelligence, or M L and A I",
    ),
    (
        r"\bsoftware as a service\s*\(SaaS\)",
        "software as a service, or S A A S",
    ),
    (
        r"\bfunction as a service\s*\(FaaS\)",
        "function as a service, or F A A S",
    ),
    (
        r"\binfrastructure as a service,?\s+or\s+IaaS\b",
        "infrastructure as a service, or I A A S",
    ),
    (r"\bextract\s*[-\u2013]\s*transform\s*[-\u2013]\s*load\b", "extract, transform, load"),
    (r"\bextract\s*[-\u2013]\s*load\s*[-\u2013]\s*transform\b", "extract, load, transform"),
    (r"\bread/write\b", "read and write"),
    (r"\breads/writes\b", "reads and writes"),
    (r"\brequest/response\b", "request and response"),
    (r"\bpublish/subscribe\b", "publish and subscribe"),
    (r"\bclient/server\b", "client and server"),
    (r"\bencoding/decoding\b", "encoding and decoding"),
    (r"\band/or\b", "and or"),
    (r"\beither/or\b", "either or"),
    (r"\bto/from\b", "to and from"),
    (r"\bweb/mobile\b", "web and mobile"),
    (r"\bfraud/abuse\b", "fraud and abuse"),
    (r"\btransactional/analytical\b", "transactional and analytical"),
    (r"\bOperational/OLTP\b", "Operational and O L T P"),
    (r"\bAnalytical/OLAP\b", "Analytical and O L A P"),
    (r"\bDevOps/SRE\b", "Dev Ops and S R E"),
    (r"\bAMQP/JMS(?:-style)?\b", "A M Q P and Java Message Service style"),
    (r"\bHTTP/1\.1\b", "H T T P version one point one"),
    (r"\bJSON Schema\b", "Jason Schema"),
    (r"\bSSTables\b", "sorted string tables"),
    (r"\bSSTable\b", "sorted string table"),
    (r"\btolerance/high availability\b", "tolerance and high availability"),
    (r"\bPandas/NumPy\b", "Pandas and NumPy"),
    (r"\bXML/JSON\b", "X M L and Jason"),
    (r"\bJSON/XML\b", "Jason and X M L"),
    (r"\bSSL/TLS\b", "S S L and T L S"),
    (r"\bTLS/SSL\b", "T L S and S S L"),
    (r"\bactive/passive\b", "active and passive"),
    (r"\bactive/active\b", "active active"),
    (r"\binsertion/update\b", "insertion and update"),
    (r"\binsertions/deletions\b", "insertions and deletions"),
    (r"\bwrite/erase\b", "write and erase"),
    (r"\bshared/exclusive\b", "shared and exclusive"),
    (r"\bairplane/theater\b", "airplane or theater"),
    (r"\bbatch/stream\b", "batch and stream"),
    (r"\bstreaming/event-driven\b", "streaming and event driven"),
    (r"\be\.g\.,?", "for example,"),
    (r"\bi\.e\.,?", "that is,"),
    (r"\betc\.", "and so on."),
    (r"\bvs\.", "versus"),
    (r"\bNo\.", "number"),
    (r"\bFig\.", "Figure"),
    (r"\bOpenAPI\b", "Open A P I"),
    (r"\bgRPC\b", "G R P C"),
)


DEFAULT_FIRST_USE_EXPANSIONS = {
    "CAS": ("compare and set", "C A S"),
    "CDC": ("change data capture", "C D C"),
    "CRDTs": ("conflict free replicated data types", "C R D T's"),
    "CRDT": ("conflict free replicated data type", "C R D T"),
    "ELT": ("extract, load, transform", "E L T"),
    "ETL": ("extract, transform, load", "E T L"),
    "FaaS": ("function as a service", "F A A S"),
    "HTAP": ("hybrid transactional and analytical processing", "H T A P"),
    "IaaS": ("infrastructure as a service", "I A A S"),
    "LSM": ("log structured merge", "L S M"),
    "LWW": ("last writer wins", "L W W"),
    "ML/AI": ("machine learning and artificial intelligence", "M L and A I"),
    "MVCC": ("multi version concurrency control", "M V C C"),
    "OLAP": ("online analytical processing", "O L A P"),
    "OLTP": ("online transaction processing", "O L T P"),
    "RPC": ("remote procedure call", "R P C"),
    "SaaS": ("software as a service", "S A A S"),
    "SQL": ("structured query language", "S Q L"),
    "SSI": ("serializable snapshot isolation", "S S I"),
    "WAL": ("write ahead log", "W A L"),
}


DEFAULT_REPLACEMENTS = {
    "ACID": "acid",
    "AI": "A I",
    "AL": "A L",
    "AMQP": "A M Q P",
    "AP": "A P",
    "API": "A P I",
    "ASCII": "A S C I I",
    "ASN.1": "A S N point one",
    "ATM": "A T M",
    "AWS": "A W S",
    "BASE": "base",
    "BI": "B I",
    "BPMN": "B P M N",
    "BSON": "B S O N",
    "B/C": "B slash C",
    "CAP": "cap",
    "CAS": "compare and set",
    "CCPA": "C C P A",
    "CDC": "C D C",
    "CEP": "C E P",
    "COBOL": "COBOL",
    "CPU": "C P U",
    "CQRS": "C Q R S",
    "CRDT": "C R D T",
    "CRM": "C R M",
    "CSV": "C S V",
    "DB": "D B",
    "DBA": "D B A",
    "DC": "D C",
    "DDD": "D D D",
    "DFS": "D F S",
    "DNS": "D N S",
    "DST": "D S T",
    "DVD": "D V D",
    "DevOps": "Dev Ops",
    "EBS": "E B S",
    "ECC": "E C C",
    "EE": "E E",
    "ELT": "E L T",
    "ETL": "E T L",
    "EU": "E U",
    "FaaS": "F A A S",
    "FLP": "F L P",
    "FUSE": "fuse",
    "GC": "G C",
    "GB": "gigabytes",
    "GDPR": "G D P R",
    "GPU": "G P U",
    "GPS": "G P S",
    "BigQuery": "Big Query",
    "CockroachDB": "Cockroach D B",
    "CouchDB": "Couch D B",
    "DataFrame": "Data Frame",
    "DataFrames": "Data Frames",
    "DynamoDB": "Dynamo D B",
    "FoundationDB": "Foundation D B",
    "GUI": "G U I",
    "GraphQL": "Graph Q L",
    "HBase": "H Base",
    "HDFS": "H D F S",
    "HNSW": "H N S W",
    "HPC": "H P C",
    "HTAP": "H T A P",
    "HTML": "H T M L",
    "HTTP": "H T T P",
    "IBM": "I B M",
    "ID": "I D",
    "IDL": "I D L",
    "I/O": "input output",
    "IaaS": "I A A S",
    "IP": "I P",
    "IVF": "I V F",
    "IVM": "I V M",
    "InnoDB": "Inno D B",
    "JDBC": "J D B C",
    "JMS": "Java Message Service",
    "JSON": "Jason",
    "JTA": "J T A",
    "JVM": "J V M",
    "LD": "L D",
    "LLM": "L L M",
    "KiB": "kibibytes",
    "L0": "level zero",
    "L1": "level one",
    "LMDB": "L M D B",
    "LSM": "L S M",
    "LWW": "L W W",
    "MapReduce": "Map Reduce",
    "MB": "megabytes",
    "ML": "M L",
    "ML/AI": "machine learning and artificial intelligence",
    "MLflow": "M L flow",
    "MVCC": "M V C C",
    "MongoDB": "Mongo D B",
    "MySQL": "My S Q L",
    "NAS": "N A S",
    "NGINX": "engine x",
    "NFS": "N F S",
    "NLP": "N L P",
    "N3": "N three",
    "NoSQL": "No S Q L",
    "NTP": "N T P",
    "OLAP": "O L A P",
    "OLTP": "O L T P",
    "OBT": "O B T",
    "ORM": "O R M",
    "ORC": "O R C",
    "OT": "O T",
    "PCI": "P C I",
    "PL/SQL": "P L S Q L",
    "PostgreSQL": "Postgres Q L",
    "QPS": "Q P S",
    "R2": "R two",
    "RDF": "R D F",
    "RDMA": "R D M A",
    "REST": "rest",
    "RPC": "R P C",
    "RAID": "raid",
    "RAC": "R A C",
    "RAM": "ram",
    "S3": "S three",
    "SAN": "S A N",
    "SLA": "S L A",
    "SLO": "S L O",
    "SOA": "S O A",
    "SOC": "S O C",
    "SOAP": "soap",
    "SKU": "S K U",
    "SPOF": "S P O F",
    "SPARQL": "sparkle",
    "SQL": "S Q L",
    "SSL": "S S L",
    "SSI": "S S I",
    "SSD": "S S D",
    "SSTable": "sorted string table",
    "SQLite": "S Q Lite",
    "SaaS": "S A A S",
    "SRE": "S R E",
    "TCP": "T C P",
    "TCP/IP": "T C P slash I P",
    "TDD": "T D D",
    "TFX": "T F X",
    "TIBCO": "T I B C O",
    "TiDB": "T I D B",
    "TLS": "T L S",
    "TLA": "T L A",
    "UDP": "U D P",
    "UI": "U I",
    "URL": "U R L",
    "US": "U S",
    "UTC": "U T C",
    "UTF-8": "U T F eight",
    "UUID": "U U I D",
    "VM": "V M",
    "VFS": "V F S",
    "VoltDB": "Volt D B",
    "WAL": "W A L",
    "POSIX": "P O S I X",
    "XA": "X A",
    "XFS": "X F S",
    "XML": "X M L",
    "YAML": "YAML",
    "YARN": "yarn",
    "ZooKeeper": "Zoo Keeper",
}


DEFAULT_MODEL = TTSNormalizationModel()


def text_for_tts(text):
    return DEFAULT_MODEL.normalize(text)
