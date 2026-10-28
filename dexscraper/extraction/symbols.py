"""Token symbol heuristics used by :class:`dexscraper.scraper.DexScraper`."""

import logging
import re
from typing import Any

# Keep the historical logger name so existing logging config still applies.
logger = logging.getLogger("dexscraper.scraper")


class SymbolExtractionMixin:
    """Find likely token symbols and names in decoded message text."""

    def _extract_real_token_names(
        self, printable: str, data_start: int
    ) -> dict[int, str]:
        """Extract real token symbols using proven deep analysis patterns."""
        token_names = {}

        # Proven patterns from analyze_protocol_deep.py
        patterns = [
            r'"symbol"\s*:\s*"([^"]+)"',  # JSON-like
            r"symbol\s*:\s*([A-Z0-9]{2,10})",  # Simple format
            r"\$([A-Z]{2,10})\b",  # Dollar prefix
            r'"name"\s*:\s*"([^"]+)"',  # Token name
            r"token\s*:\s*([A-Z0-9]{2,10})",  # Token field
        ]

        all_symbols = []
        for pattern in patterns:
            matches = re.findall(pattern, printable, re.IGNORECASE)
            for match in matches:
                if match and len(match) >= 2:
                    all_symbols.append(match)

        # Look for uppercase sequences that could be tokens
        uppercase_pattern = r"\b([A-Z]{2,10})\b"
        uppercase_matches = re.findall(uppercase_pattern, printable)

        # Validated blacklist from deep analysis
        blacklist = {
            "HTTP",
            "HTTPS",
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "JSON",
            "XML",
            "HTML",
            "CSS",
            "JS",
            "API",
            "URL",
            "URI",
            "TCP",
            "UDP",
            "DNS",
            "SSL",
            "TLS",
            "UTF",
            "ASCII",
            "BASE",
            "TRUE",
            "FALSE",
            "NULL",
            "VOID",
            "INT",
            "FLOAT",
            "DOUBLE",
        }

        for match in uppercase_matches:
            if match not in blacklist:
                all_symbols.append(match)

        # Look for mixed-case token names
        mixed_pattern = r"\b([A-Z][a-z]{2,15})\b"
        mixed_matches = re.findall(mixed_pattern, printable)

        # Filter out common English words
        english_words = {
            "The",
            "And",
            "For",
            "Are",
            "But",
            "Not",
            "You",
            "All",
            "Can",
            "Had",
            "Her",
            "Was",
            "One",
            "Our",
            "Out",
            "Day",
            "Get",
            "Has",
            "Him",
            "His",
            "How",
            "Its",
            "May",
            "New",
            "Now",
            "Old",
            "See",
            "Two",
            "Way",
            "Who",
            "Boy",
            "Did",
            "Http",
            "Https",
            "Json",
            "Server",
            "Client",
            "Request",
            "Response",
            "Error",
            "Success",
            "Failed",
            "Retry",
        }

        for match in mixed_matches:
            if match not in english_words:
                all_symbols.append(match)

        # Remove duplicates and sort by frequency
        symbol_counts: dict[str, int] = {}
        for symbol in all_symbols:
            symbol_upper = symbol.upper()
            symbol_counts[symbol_upper] = symbol_counts.get(symbol_upper, 0) + 1

        # Sort by frequency (most frequent = most likely real token)
        sorted_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)

        logger.debug(f"Found {len(sorted_symbols)} unique potential token symbols")
        for symbol, count in sorted_symbols[:20]:  # Top 20 most frequent
            pos = printable.find(symbol)
            if pos >= 0:
                token_names[data_start + pos] = symbol

        return token_names

    def _extract_token_symbols(
        self, text: str, data_start: int
    ) -> list[dict[str, Any]]:
        """Extract potential token symbols and names from binary data."""
        import re

        token_symbols: list[dict[str, Any]] = []
        symbol_counts: dict[str, int] = {}  # Track frequency of each symbol

        # Pattern 1: Common crypto token patterns (2-10 uppercase letters)
        crypto_pattern = re.compile(r"\b[A-Z]{2,10}\b")
        matches = crypto_pattern.findall(text)

        # Count occurrences of each symbol
        for match in matches:
            symbol_counts[match] = symbol_counts.get(match, 0) + 1

        # Extended blacklist based on deep analysis findings
        blacklist = {
            "HTTP",
            "HTTPS",
            "API",
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "JSON",
            "XML",
            "HTML",
            "CSS",
            "JS",
            "PNG",
            "JPG",
            "GIF",
            "TRUE",
            "FALSE",
            "NULL",
            "VOID",
            "INT",
            "CHAR",
            "BOOL",
            "STRING",
            "AND",
            "OR",
            "NOT",
            "IF",
            "ELSE",
            "FOR",
            "WHILE",
            "DO",
            "RETURN",
            "CONST",
            "VAR",
            "LET",
            "NEW",
            "THIS",
            "SUPER",
            "TRY",
            "CATCH",
            "URL",
            "URI",
            "TCP",
            "UDP",
            "DNS",
            "SSL",
            "TLS",
            "UTF",
            "ASCII",
            "BASE",
            "ERROR",
            "INFO",
            "WARN",
            "DEBUG",
            "TRACE",
        }

        # Whitelist known good token symbols from our analysis
        whitelist = {
            "SOL",
            "USDC",
            "USD",
            "WLFI",
            "COIN",
            "MROCKS",
            "OTC",
            "KAIROS",
            "EMULITES",
            "LYN",
            "FINANCE",
            "SHOT",
            "HOPE",
            "AA",
            "EA",
            "FA",
            "PEPE",
            "DOGE",
            "SHIB",
            "BONK",
        }

        for match, count in symbol_counts.items():
            # Prioritize whitelisted tokens
            if match in whitelist:
                pos = text.find(match)
                if pos >= 0:
                    token_symbols.append(
                        {
                            "symbol": match,
                            "position": data_start + pos,
                            "type": "whitelisted",
                            "confidence": 0.95,
                            "frequency": count,
                        }
                    )
            # Skip blacklisted terms
            elif match not in blacklist:
                # Higher confidence for symbols that appear multiple times
                confidence = 0.7 if count == 1 else min(0.7 + (count * 0.05), 0.9)

                pos = text.find(match)
                if pos >= 0:
                    token_symbols.append(
                        {
                            "symbol": match,
                            "position": data_start + pos,
                            "type": "crypto_symbol",
                            "confidence": confidence,
                            "frequency": count,
                        }
                    )

        # Pattern 2: Look for tokens with $ prefix (like $PEPE, $DOGE)
        dollar_pattern = re.compile(r"\$[A-Z]{2,10}\b")
        dollar_matches = dollar_pattern.findall(text)

        for match in set(dollar_matches):
            symbol = match[1:]  # Remove $ prefix
            pos = text.find(match)
            if pos >= 0:
                token_symbols.append(
                    {
                        "symbol": symbol,
                        "position": data_start + pos,
                        "type": "dollar_prefixed",
                        "confidence": 0.9,
                    }
                )

        # Pattern 3: Look for tokens near "symbol" or "name" keywords
        symbol_context_pattern = re.compile(
            r"(?:symbol|name|token)[:\s]*([A-Za-z0-9]{2,10})", re.IGNORECASE
        )
        context_matches = symbol_context_pattern.findall(text)

        for match in set(context_matches):
            if len(match) >= 2 and match.upper() not in ["SYMBOL", "NAME", "TOKEN"]:
                pos = text.find(match)
                if pos >= 0:
                    token_symbols.append(
                        {
                            "symbol": match.upper(),
                            "position": data_start + pos,
                            "type": "context_based",
                            "confidence": 0.8,
                        }
                    )

        # Pattern 4: Mixed case tokens (like "Coiny", "Phantom")
        mixed_case_pattern = re.compile(r"\b[A-Z][a-z]{2,15}\b")
        mixed_matches = mixed_case_pattern.findall(text)

        for match in set(mixed_matches):
            # Filter out common English words
            if match.lower() not in [
                "the",
                "and",
                "for",
                "are",
                "but",
                "not",
                "you",
                "all",
                "can",
                "had",
                "her",
                "was",
                "one",
                "our",
                "out",
                "day",
                "get",
                "has",
                "him",
                "his",
                "how",
                "its",
                "may",
                "new",
                "now",
                "old",
                "see",
                "two",
                "way",
                "who",
                "boy",
                "did",
                "does",
                "each",
                "find",
                "here",
                "just",
                "like",
                "long",
                "make",
                "many",
                "over",
                "part",
                "some",
                "time",
                "very",
                "what",
                "with",
                "have",
                "from",
                "they",
                "know",
                "want",
                "been",
                "good",
                "much",
                "some",
                "time",
                "very",
                "when",
                "come",
                "could",
                "state",
                "there",
                "think",
                "where",
                "will",
                "would",
                "about",
                "after",
                "again",
                "below",
                "being",
                "both",
                "could",
                "every",
                "first",
                "found",
                "great",
                "group",
                "large",
                "last",
                "left",
                "life",
                "little",
                "never",
                "next",
                "often",
                "other",
                "own",
                "right",
                "small",
                "still",
                "such",
                "take",
                "than",
                "them",
                "well",
                "were",
                "Http",
                "Https",
                "Json",
            ]:
                pos = text.find(match)
                if pos >= 0:
                    token_symbols.append(
                        {
                            "symbol": match,
                            "position": data_start + pos,
                            "type": "mixed_case",
                            "confidence": 0.5,
                        }
                    )

        # Sort by confidence and remove low-quality matches
        token_symbols.sort(key=lambda x: x["confidence"], reverse=True)

        # Return top 20 most confident symbols
        return token_symbols[:20]

    def _extract_best_token_symbol(
        self, metadata: dict[str, list[dict[str, Any]]], index: int
    ) -> str:
        """Extract the best token symbol from metadata, with fallback to placeholder."""
        tokens = metadata.get("tokens", [])

        if not tokens:
            return f"UNKNOWN_{index:02d}"

        # Sort by confidence, frequency, and type preference
        def symbol_score(token_info: dict[str, Any]) -> float:
            confidence = token_info.get("confidence", 0.0)
            score = float(confidence) if isinstance(confidence, (int, float)) else 0.0

            # Boost score based on frequency (tokens appearing multiple times are more likely correct)
            frequency_raw = token_info.get("frequency", 1)
            frequency = (
                int(frequency_raw) if isinstance(frequency_raw, (int, float)) else 1
            )
            if frequency > 1:
                score += min(frequency * 0.02, 0.2)  # Up to 0.2 bonus for frequency

            # Type-based bonuses
            token_type = str(token_info.get("type", ""))
            if token_type == "whitelisted":  # nosec B105 - token classifier label
                score += 0.5  # Strong preference for known tokens
            elif token_type == "dollar_prefixed":  # nosec B105 - token classifier label
                score += 0.3
            elif token_type == "context_based":  # nosec B105 - token classifier label
                score += 0.2
            elif token_type == "crypto_symbol":  # nosec B105 - token classifier label
                score += 0.1

            return score

        tokens.sort(key=symbol_score, reverse=True)

        # Filter for quality - skip single letters unless whitelisted
        for token in tokens:
            symbol_raw = token.get("symbol")
            if not isinstance(symbol_raw, str):
                continue
            symbol = symbol_raw

            # Skip single letters unless they're whitelisted (like "AA", "EA", "FA" from our analysis)
            if len(symbol) == 1 and str(token.get("type", "")) != "whitelisted":
                continue

            # Accept symbols between 2-10 characters that are alphanumeric
            if (
                2 <= len(symbol) <= 10
                and symbol.replace("_", "").replace("-", "").isalnum()
            ):
                return symbol.upper()  # Ensure uppercase for consistency

        # If no good symbol found, use the first one if available
        if tokens:
            first_symbol = tokens[0].get("symbol")
            if isinstance(first_symbol, str):
                return first_symbol.upper()

        # Final fallback
        return f"UNKNOWN_{index:02d}"
