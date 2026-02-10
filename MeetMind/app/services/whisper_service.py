"""Whisper speech-to-text service using OpenAI API with FFmpeg chunking and parallel processing"""

import os
import subprocess
import tempfile
import asyncio
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from fastapi import HTTPException
from app.config import settings


class WhisperService:
    """Service for transcribing audio using OpenAI Whisper API with FFmpeg chunking"""
    
    # OpenAI Whisper API file size limit (25 MB)
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB in bytes
    
    # Maximum file size to process (100 MB - configurable limit)
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
    
    # Chunk settings
    CHUNK_DURATION_SECONDS = 600  # 10 minutes
    OVERLAP_SECONDS = 10  # 10 seconds overlap between chunks
    
    # Parallel processing
    MAX_PARALLEL_TRANSCRIPTIONS = 3  # Process up to 3 chunks simultaneously
    
    @classmethod
    def check_ffmpeg_available(cls) -> bool:
        """Check if FFmpeg is available on the system."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @classmethod
    def get_audio_duration(cls, file_path: str) -> float:
        """
        Get audio duration in seconds using FFprobe.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Duration in seconds
        """
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    file_path
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            return float(result.stdout.strip())
        except Exception:
            # Fallback: estimate from file size (rough: 1 MB ≈ 60 seconds for typical audio)
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            return file_size_mb * 60
    
    @classmethod
    def validate_audio_file(cls, file_path: str) -> Tuple[float, int]:
        """
        Validate audio file and get metadata.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (duration_in_minutes, file_size_in_bytes)
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Check maximum upload size
            if file_size > cls.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large ({file_size / (1024 * 1024):.1f} MB). "
                           f"Maximum allowed: {cls.MAX_UPLOAD_SIZE / (1024 * 1024):.0f} MB"
                )
            
            # Get duration
            duration_seconds = cls.get_audio_duration(file_path)
            duration_minutes = duration_seconds / 60
            
            # Validate duration (max 2 hours for cost control)
            if duration_minutes > 120:
                raise HTTPException(
                    status_code=413,
                    detail=f"Audio too long ({duration_minutes:.1f} minutes). "
                           f"Maximum allowed: 120 minutes (2 hours)"
                )
            
            print(f"✓ Validated: {duration_minutes:.1f}min, {file_size / (1024 * 1024):.1f}MB")
            
            return duration_minutes, file_size
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audio file: {str(e)}"
            )
    
    @classmethod
    def split_audio_with_ffmpeg(cls, input_path: str, duration_seconds: float) -> List[str]:
        """
        Split audio file into chunks using FFmpeg with overlap.
        
        Args:
            input_path: Path to original audio file
            duration_seconds: Total duration in seconds
            
        Returns:
            List of paths to audio chunk files
        """
        print(f"⚡ Splitting into chunks (10s overlap)...")
        
        # Calculate number of chunks needed
        effective_chunk_duration = cls.CHUNK_DURATION_SECONDS - cls.OVERLAP_SECONDS
        num_chunks = max(1, int((duration_seconds - cls.OVERLAP_SECONDS) / effective_chunk_duration) + 1)
        
        print(f"  {num_chunks} chunks × {cls.CHUNK_DURATION_SECONDS / 60:.0f}min each")
        
        chunk_paths = []
        suffix = Path(input_path).suffix
        
        for i in range(num_chunks):
            # Calculate start time with overlap
            if i == 0:
                start_time = 0
            else:
                start_time = i * effective_chunk_duration
            
            # Calculate duration for this chunk
            remaining_duration = duration_seconds - start_time
            chunk_duration = min(cls.CHUNK_DURATION_SECONDS, remaining_duration)
            
            # Create temporary file for chunk
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                chunk_path = tmp_file.name
            
            try:
                # Use FFmpeg to extract chunk (fast codec copy)
                subprocess.run(
                    [
                        "ffmpeg",
                        "-i", input_path,
                        "-ss", str(start_time),
                        "-t", str(chunk_duration),
                        "-c", "copy",  # Copy codec (fast, no re-encoding)
                        "-y",  # Overwrite output file
                        "-loglevel", "error",  # Only show errors
                        chunk_path  # Output file
                    ],
                    capture_output=True,
                    check=True,
                    timeout=60
                )
                
                chunk_size = os.path.getsize(chunk_path)
                
                # Validate chunk size
                if chunk_size > cls.MAX_FILE_SIZE:
                    # Clean up chunks created so far
                    for path in chunk_paths:
                        try:
                            os.remove(path)
                        except:
                            pass
                    os.remove(chunk_path)
                    
                    raise HTTPException(
                        status_code=413,
                        detail=f"Chunk {i+1} too large ({chunk_size / (1024 * 1024):.1f}MB). "
                               f"Re-encode at lower bitrate."
                    )
                
                chunk_paths.append(chunk_path)
                
            except subprocess.CalledProcessError as e:
                # Clean up on error
                for path in chunk_paths:
                    try:
                        os.remove(path)
                    except:
                        pass
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                
                error_msg = e.stderr.decode() if e.stderr else str(e)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to split audio: {error_msg}"
                )
        
        print(f"  ✓ Split complete ({sum(os.path.getsize(p) for p in chunk_paths) / (1024 * 1024):.1f}MB total)")
        return chunk_paths
    
    @classmethod
    def transcribe_chunk(cls, chunk_path: str, chunk_index: int, total_chunks: int) -> Tuple[int, str]:
        """
        Transcribe a single audio chunk.
        
        Args:
            chunk_path: Path to audio chunk file
            chunk_index: Index of this chunk (0-based)
            total_chunks: Total number of chunks
            
        Returns:
            Tuple of (chunk_index, transcribed_text)
        """
        try:
            client = OpenAI(api_key=settings.openai_api_key)
            
            with open(chunk_path, "rb") as audio_file:
                transcript_response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            
            transcript = transcript_response.text.strip()
            print(f"  ✓ Chunk {chunk_index + 1}/{total_chunks}: {len(transcript)} chars")
            
            return (chunk_index, transcript)
        except Exception as e:
            print(f"  ✗ Chunk {chunk_index + 1}/{total_chunks} failed: {str(e)}")
            raise
    
    @classmethod
    def transcribe_chunks_parallel(cls, chunk_paths: List[str]) -> List[str]:
        """
        Transcribe multiple chunks in parallel for speed.
        
        Args:
            chunk_paths: List of paths to chunk files
            
        Returns:
            List of transcripts in order
        """
        total_chunks = len(chunk_paths)
        print(f"⚡ Transcribing {total_chunks} chunks in parallel (max {cls.MAX_PARALLEL_TRANSCRIPTIONS} at once)...")
        
        # Use ThreadPoolExecutor for parallel API calls
        transcripts = [None] * total_chunks
        
        with ThreadPoolExecutor(max_workers=cls.MAX_PARALLEL_TRANSCRIPTIONS) as executor:
            # Submit all transcription tasks
            future_to_index = {
                executor.submit(cls.transcribe_chunk, chunk_path, i, total_chunks): i
                for i, chunk_path in enumerate(chunk_paths)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_index):
                try:
                    chunk_index, transcript = future.result()
                    transcripts[chunk_index] = transcript
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Transcription failed: {str(e)}"
                    )
        
        print(f"  ✓ All chunks transcribed!")
        return transcripts
    
    @classmethod
    def merge_overlapping_transcripts(cls, transcripts: List[str]) -> str:
        """
        Merge transcripts from overlapping chunks.
        
        Args:
            transcripts: List of transcript strings
            
        Returns:
            Combined transcript
        """
        return " ".join(transcripts)
    
    @classmethod
    def transcribe_audio(cls, audio_path: str) -> str:
        """
        Transcribe audio file to text using OpenAI Whisper API.
        Automatically chunks files larger than 25 MB using FFmpeg with parallel processing.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text
            
        Raises:
            HTTPException: If transcription fails
        """
        chunk_paths = []
        try:
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for Whisper API")
            
            # Validate audio file and get metadata
            duration_minutes, file_size = cls.validate_audio_file(audio_path)
            
            print(f"\n🎵 Processing: {Path(audio_path).name}")
            
            # Estimate cost (Whisper API: $0.006 per minute)
            estimated_cost = duration_minutes * 0.006
            print(f"💰 Cost: ${estimated_cost:.3f}")
            
            # Check if chunking is needed
            if file_size > cls.MAX_FILE_SIZE:
                print(f"⚠️  Large file - using FFmpeg chunking...")
                
                # Check if FFmpeg is available
                if not cls.check_ffmpeg_available():
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large ({file_size / (1024 * 1024):.1f}MB). "
                               f"Install FFmpeg: sudo apt-get install ffmpeg"
                    )
                
                # Split into chunks using FFmpeg
                chunk_paths = cls.split_audio_with_ffmpeg(audio_path, duration_minutes * 60)
                
                # Transcribe chunks in parallel for speed
                transcripts = cls.transcribe_chunks_parallel(chunk_paths)
                
                # Merge transcripts
                full_transcript = cls.merge_overlapping_transcripts(transcripts)
                
                print(f"✅ Complete: {len(full_transcript)} characters\n")
                
                return full_transcript
            
            else:
                # File is small enough, transcribe directly
                print(f"🎤 Transcribing...")
                
                client = OpenAI(api_key=settings.openai_api_key)
                
                with open(audio_path, "rb") as audio_file:
                    transcript_response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="en"
                    )
                
                transcript = transcript_response.text.strip()
                
                if not transcript:
                    raise ValueError("Transcription resulted in empty text")
                
                print(f"✅ Complete: {len(transcript)} characters\n")
                
                return transcript
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to transcribe audio: {str(e)}"
            )
        finally:
            # Clean up chunk files if they were created
            if chunk_paths:
                for chunk_path in chunk_paths:
                    if os.path.exists(chunk_path):
                        try:
                            os.remove(chunk_path)
                        except:
                            pass
                print(f"🧹 Cleaned up {len(chunk_paths)} temp files")
