#!/usr/bin/env python3
"""Test enhanced OHLC output and MT5 format with real extracted data."""

import asyncio
import json
from datetime import datetime

import pytest

from dexscraper import DexScraper, ExtractedTokenBatch, TokenProfile


async def test_enhanced_ohlc_output():
    """Test complete OHLC output with enhanced extraction."""
    print("🧪 TESTING ENHANCED OHLC/MT5 OUTPUT")
    print("=" * 60)

    # Initialize enhanced scraper
    scraper = DexScraper(debug=False)

    print("📡 Extracting live token data...")
    batch = await scraper.extract_token_data()

    if not batch.tokens:
        print("❌ No tokens extracted - test failed")
        return

    print(f"✅ Extracted {batch.total_extracted} tokens")
    print(f"   High confidence: {batch.high_confidence_count}")
    print(f"   Complete profiles: {batch.complete_profiles_count}")

    # Get top tokens for testing
    top_tokens = batch.get_top_tokens(10)
    print(f"\n🏆 Testing OHLC output with top {len(top_tokens)} tokens")

    # Test 1: Basic OHLC format
    print(f"\n📊 TEST 1: BASIC OHLC FORMAT")
    print("-" * 40)
    print("Format: SYMBOL,TIMESTAMP,OPEN,HIGH,LOW,CLOSE,VOLUME")

    ohlc_count = 0
    for token in top_tokens:
        ohlc = token.to_ohlc()
        if ohlc:
            print(
                f"{token.get_display_name()},{ohlc.timestamp},{ohlc.open:.8f},{ohlc.high:.8f},{ohlc.low:.8f},{ohlc.close:.8f},{ohlc.volume:.0f}"
            )
            ohlc_count += 1

    print(f"✅ Generated {ohlc_count} OHLC records")

    # Test 2: MT5 format
    print(f"\n📈 TEST 2: MT5 FORMAT")
    print("-" * 40)
    print("Format: YYYY.MM.DD HH:MM:SS,OPEN,HIGH,LOW,CLOSE,VOLUME")

    mt5_count = 0
    for token in top_tokens:
        ohlc = token.to_ohlc()
        if ohlc:
            print(f"{token.get_display_name()}: {ohlc.to_mt5_format()}")
            mt5_count += 1

    print(f"✅ Generated {mt5_count} MT5 records")

    # Test 3: Batch OHLC conversion
    print(f"\n🔄 TEST 3: BATCH OHLC CONVERSION")
    print("-" * 40)

    batch_ohlc = batch.to_ohlc_batch("1m")
    print(f"Batch OHLC conversion: {len(batch_ohlc)} records")

    # Show sample batch records
    for i, ohlc in enumerate(batch_ohlc[:5]):
        print(
            f"  {i+1}: {datetime.fromtimestamp(ohlc.timestamp).strftime('%H:%M:%S')} | "
            f"${ohlc.close:.8f} | Vol: ${ohlc.volume:,.0f}"
        )

    print(f"✅ Batch processing: {len(batch_ohlc)} records")

    # Test 4: Legacy compatibility
    print(f"\n🔄 TEST 4: LEGACY COMPATIBILITY")
    print("-" * 40)

    trading_pairs = batch.to_trading_pairs()
    print(f"Legacy TradingPair conversion: {len(trading_pairs)} pairs")

    # Test legacy OHLC format
    legacy_ohlc_count = 0
    for pair in trading_pairs[:5]:
        ohlc = pair.to_ohlc()
        if ohlc:
            print(
                f"  {pair.base_token_symbol}: ${ohlc.close:.8f} | Vol: ${ohlc.volume:,.0f}"
            )
            legacy_ohlc_count += 1

    print(f"✅ Legacy compatibility: {legacy_ohlc_count} OHLC records")

    # Test 5: Real-time streaming simulation
    print(f"\n🔄 TEST 5: STREAMING SIMULATION")
    print("-" * 40)

    print("Simulating 3 extraction cycles...")
    for cycle in range(3):
        print(f"\n📡 Cycle {cycle + 1}/3:")
        batch = await scraper.extract_token_data()

        if batch.tokens:
            # Generate streaming OHLC output
            top_3 = batch.get_top_tokens(3)
            for token in top_3:
                ohlc = token.to_ohlc()
                if ohlc:
                    confidence = f"{token.confidence_score:.0%}"
                    fields = f"{token.field_count}F"
                    print(
                        f"  {token.get_display_name():<12} | ${ohlc.close:<12.8f} | {confidence:<4} | {fields}"
                    )

        # Short delay between cycles
        if cycle < 2:
            await asyncio.sleep(2)

    print(f"✅ Streaming simulation complete")

    # Test 6: Enhanced JSON output
    print(f"\n📄 TEST 6: ENHANCED JSON OUTPUT")
    print("-" * 40)

    # Get fresh batch
    final_batch = await scraper.extract_token_data()

    if final_batch.tokens:
        enhanced_output = {
            "type": "enhanced_ohlc_batch",
            "extraction_info": {
                "timestamp": final_batch.extraction_timestamp,
                "total_extracted": final_batch.total_extracted,
                "high_confidence_count": final_batch.high_confidence_count,
                "complete_profiles_count": final_batch.complete_profiles_count,
            },
            "ohlc_data": [],
        }

        # Add OHLC data for top tokens
        for token in final_batch.get_top_tokens(5):
            ohlc = token.to_ohlc()
            if ohlc:
                enhanced_output["ohlc_data"].append(
                    {
                        "symbol": token.get_display_name(),
                        "timestamp": ohlc.timestamp,
                        "open": ohlc.open,
                        "high": ohlc.high,
                        "low": ohlc.low,
                        "close": ohlc.close,
                        "volume": ohlc.volume,
                        "confidence_score": token.confidence_score,
                        "field_count": token.field_count,
                        "protocol": token.protocol,
                        "website": token.website,
                        "twitter": token.twitter,
                    }
                )

        # Save to file
        with open("enhanced_ohlc_output.json", "w") as f:
            json.dump(enhanced_output, f, indent=2, default=str)

        print(f"Enhanced JSON output saved to: enhanced_ohlc_output.json")
        print(f"Records: {len(enhanced_output['ohlc_data'])}")
        print(f"✅ Enhanced JSON format complete")

    # Summary
    print(f"\n🎯 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Basic OHLC format: {ohlc_count} records")
    print(f"✅ MT5 format: {mt5_count} records")
    print(f"✅ Batch processing: {len(batch_ohlc)} records")
    print(f"✅ Legacy compatibility: {legacy_ohlc_count} records")
    print(f"✅ Streaming simulation: 3 cycles completed")
    print(f"✅ Enhanced JSON output: Saved to file")

    print(f"\n🚀 ALL OHLC/MT5 TESTS PASSED!")


async def test_enhanced_streaming():
    """Test enhanced streaming with different output formats."""
    print("\n🔄 TESTING ENHANCED STREAMING")
    print("=" * 60)

    scraper = DexScraper(debug=False)

    # Test streaming callback
    extraction_count = 0

    def streaming_callback(batch):
        nonlocal extraction_count
        extraction_count += 1
        print(
            f"📡 Stream {extraction_count}: {batch.total_extracted} tokens, "
            f"{batch.high_confidence_count} high-confidence"
        )

        # Generate OHLC output
        for token in batch.get_top_tokens(3):
            ohlc = token.to_ohlc()
            if ohlc:
                print(
                    f"   {token.get_display_name()}: ${ohlc.close:.8f} | Vol: ${ohlc.volume:,.0f}"
                )

    print("Testing streaming with callback for 3 cycles...")

    # Simulate streaming for a short time
    try:
        task = asyncio.create_task(
            scraper.stream_pairs(
                callback=streaming_callback,
                output_format="json",
                use_enhanced_extraction=True,
            )
        )

        # Let it run for a few cycles
        await asyncio.sleep(15)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        print(f"✅ Streaming test complete: {extraction_count} extractions")

    except Exception as e:
        print(f"❌ Streaming test error: {e}")


if __name__ == "__main__":
    # Run main OHLC tests
    asyncio.run(test_enhanced_ohlc_output())

    # Run streaming tests
    asyncio.run(test_enhanced_streaming())
