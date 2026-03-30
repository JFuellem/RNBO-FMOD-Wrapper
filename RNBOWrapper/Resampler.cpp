#include "Resampler.hpp"

#include <cmath>

namespace RNBOFMODResampler {

namespace {
constexpr int kTaps = 32;
constexpr int kHalfTaps = kTaps / 2;

inline double Sinc(double x) {
    if (x == 0.0) {
        return 1.0;
    }
    return std::sin(M_PI * x) / (M_PI * x);
}

inline double HannWindow(double x, double radius) {
    double ax = std::fabs(x);
    if (ax >= radius) {
        return 0.0;
    }
    return 0.5 * (1.0 + std::cos(M_PI * ax / radius));
}
}  // namespace

size_t ComputeOutputFrames(size_t inputFrames, unsigned int inputSampleRate, unsigned int outputSampleRate) {
    if (inputFrames == 0 || inputSampleRate == 0 || outputSampleRate == 0) {
        return 0;
    }
    double ratio = static_cast<double>(outputSampleRate) / static_cast<double>(inputSampleRate);
    return static_cast<size_t>(std::ceil(static_cast<double>(inputFrames) * ratio));
}

bool ResampleSinc(const float* input, size_t inputFrames, unsigned int channels,
                  unsigned int inputSampleRate, unsigned int outputSampleRate,
                  float* output, size_t outputFrames) {
    if (!input || !output || inputFrames == 0 || outputFrames == 0 || channels == 0 ||
        inputSampleRate == 0 || outputSampleRate == 0) {
        return false;
    }
    if (inputSampleRate == outputSampleRate) {
        return false;
    }

    double ratio = static_cast<double>(outputSampleRate) / static_cast<double>(inputSampleRate);
    for (size_t i = 0; i < outputFrames; i++) {
        double srcPos = static_cast<double>(i) / ratio;
        long center = static_cast<long>(std::floor(srcPos));
        for (unsigned int c = 0; c < channels; c++) {
            double acc = 0.0;
            double norm = 0.0;
            for (int k = -kHalfTaps + 1; k <= kHalfTaps; k++) {
                long idx = center + k;
                if (idx < 0 || static_cast<size_t>(idx) >= inputFrames) {
                    continue;
                }
                double dist = srcPos - static_cast<double>(idx);
                double w = Sinc(dist) * HannWindow(dist, static_cast<double>(kHalfTaps));
                acc += static_cast<double>(input[idx * channels + c]) * w;
                norm += w;
            }
            if (norm != 0.0) {
                acc /= norm;
            }
            output[i * channels + c] = static_cast<float>(acc);
        }
    }

    return true;
}

}  // namespace RNBOFMODResampler
