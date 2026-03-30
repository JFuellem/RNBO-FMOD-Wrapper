#ifndef RNBO_FMOD_RESAMPLER_HPP
#define RNBO_FMOD_RESAMPLER_HPP

#include <cstddef>

namespace RNBOFMODResampler {

size_t ComputeOutputFrames(size_t inputFrames, unsigned int inputSampleRate, unsigned int outputSampleRate);
bool ResampleSinc(const float* input, size_t inputFrames, unsigned int channels,
                  unsigned int inputSampleRate, unsigned int outputSampleRate,
                  float* output, size_t outputFrames);

}

#endif
