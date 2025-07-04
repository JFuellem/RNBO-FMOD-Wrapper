//
//  RNBOWrapper.cpp
//  RNBO_FMOD
//
//  Created by Jonas Füllemann on 19.01.24.
//

#define DR_WAV_IMPLEMENTATION
#include "dr_wav.h"
#define DR_MP3_IMPLEMENTATION
#include "dr_mp3.h"

#include "RNBOWrapper.hpp"

void RNBOWrapper::Init(RNBO::PatcherFactoryFunctionPtr (*factoryProvider)(RNBO::PlatformInterface*))
{
    size_t c(0);
    do
    {
        auto patcherInterface = factoryProvider(RNBO::Platform::get())();
        rnboObj.push_back(std::make_unique<RNBO::CoreObject>(
            RNBO::UniquePtr<RNBO::PatcherInterface>(patcherInterface)));
        c++;
    } while (multiChannelExpandable && c<MAX_CHANS);
}

void RNBOWrapper::CleanupBuffers()
{
    if (deInterleaveBuffer) {
        delete[] deInterleaveBuffer;
        deInterleaveBuffer = nullptr;
    }
    
    if (interleaveBuffer) {
        delete[] interleaveBuffer;
        interleaveBuffer = nullptr;
    }
}

void RNBOWrapper::Reset()
{
    shouldGoIdle = false;
    inputsIdle = 0;
    
    rnboObj.clear();
    
    CleanupBuffers();
    
    lastChannelCount = -1;
}

bool RNBOWrapper::DecodeAudio(const void* data, size_t dataLength, char*& decodedData, size_t& decodedLengthInBytes, unsigned int& channels, unsigned int& sampleRate)
{
    // The caller of this function is responsible for freeing the memory allocated for decodedData,
    // which should be done via the callback passed to RNBO's setExternalData.

    // Try WAV
    drwav wav;
    if (drwav_init_memory(&wav, data, dataLength, NULL)) {
        drwav_uint64 frameCount = wav.totalPCMFrameCount;
        channels = wav.channels;
        sampleRate = wav.sampleRate;
        drwav_uint64 totalSampleCount = frameCount * channels;
        float* pcmData = new float[totalSampleCount];
        
        drwav_read_pcm_frames_f32(&wav, frameCount, pcmData);
        
        drwav_uninit(&wav);
        
        decodedData = reinterpret_cast<char*>(pcmData);
        decodedLengthInBytes = totalSampleCount * sizeof(float);
        return true;
    }

    // Try MP3
    drmp3 mp3;
    if (drmp3_init_memory(&mp3, data, dataLength, NULL)) {
        drmp3_uint64 pcmFrameCount = drmp3_get_pcm_frame_count(&mp3);
        channels = mp3.channels;
        sampleRate = mp3.sampleRate;
        drmp3_uint64 totalSampleCount = pcmFrameCount * channels;
        float* pcmData = new float[totalSampleCount];
        
        drmp3_read_pcm_frames_f32(&mp3, pcmFrameCount, pcmData);
        
        drmp3_uninit(&mp3);
        
        decodedData = reinterpret_cast<char*>(pcmData);
        decodedLengthInBytes = totalSampleCount * sizeof(float);
        return true;
    }

    return false;
}

namespace RNBOFMODHelpers
{
    bool CheckRNBOTag(const RNBO::CoreObject &obj, const char* tag)
    {
        return strcmp(obj.resolveTag(RNBO::TAG(tag)), tag) == 0;
    }

    bool CheckAnyRNBOSystemTag(const RNBO::CoreObject &obj)
    {
        return (CheckRNBOTag(obj, "rel_pos") || CheckRNBOTag(obj, "rel_vel") ||
                CheckRNBOTag(obj, "rel_forw") || CheckRNBOTag(obj, "rel_up") ||
                CheckRNBOTag(obj, "abs_pos") || CheckRNBOTag(obj, "abs_vel") ||
                CheckRNBOTag(obj, "abs_forw") || CheckRNBOTag(obj, "abs_up"));
    }

    void DispatchRNBOMessages(RNBO::CoreObject *obj, void* rawData)
    {
        FMOD_DSP_PARAMETER_3DATTRIBUTES* param = (FMOD_DSP_PARAMETER_3DATTRIBUTES*)rawData;
        if(CheckRNBOTag(*obj, "rel_pos"))
        {
            auto posList = RNBO::make_unique<RNBO::list>();
            posList->push(param->relative.position.x);
            posList->push(param->relative.position.y);
            posList->push(param->relative.position.z);
            obj->sendMessage(RNBO::TAG("rel_pos"), std::move(posList), RNBO::TAG(""));
        }
        if(CheckRNBOTag(*obj, "rel_vel"))
        {
            auto posList = RNBO::make_unique<RNBO::list>();
            posList->push(param->relative.velocity.x);
            posList->push(param->relative.velocity.y);
            posList->push(param->relative.velocity.z);
            obj->sendMessage(RNBO::TAG("rel_vel"), std::move(posList), RNBO::TAG(""));
        }
        if(CheckRNBOTag(*obj, "rel_forw"))
        {
            auto posList = RNBO::make_unique<RNBO::list>();
            posList->push(param->relative.forward.x);
            posList->push(param->relative.forward.y);
            posList->push(param->relative.forward.z);
            obj->sendMessage(RNBO::TAG("rel_forw"), std::move(posList), RNBO::TAG(""));
        }
        if(CheckRNBOTag(*obj, "rel_up"))
        {
            auto posList = RNBO::make_unique<RNBO::list>();
            posList->push(param->relative.up.x);
            posList->push(param->relative.up.y);
            posList->push(param->relative.up.z);
            obj->sendMessage(RNBO::TAG("rel_up"), std::move(posList), RNBO::TAG(""));
        }
        if(CheckRNBOTag(*obj, "abs_pos"))
        {
            auto posList = RNBO::make_unique<RNBO::list>();
            posList->push(param->absolute.position.x);
            posList->push(param->absolute.position.y);
            posList->push(param->absolute.position.z);
            obj->sendMessage(RNBO::TAG("abs_pos"), std::move(posList), RNBO::TAG(""));
        }
        if(CheckRNBOTag(*obj, "abs_vel"))
        {
            auto posList = RNBO::make_unique<RNBO::list>();
            posList->push(param->absolute.velocity.x);
            posList->push(param->absolute.velocity.y);
            posList->push(param->absolute.velocity.z);
            obj->sendMessage(RNBO::TAG("abs_vel"), std::move(posList), RNBO::TAG(""));
        }
        if(CheckRNBOTag(*obj, "abs_forw"))
        {
            auto posList = RNBO::make_unique<RNBO::list>();
            posList->push(param->absolute.forward.x);
            posList->push(param->absolute.forward.y);
            posList->push(param->absolute.forward.z);
            obj->sendMessage(RNBO::TAG("abs_forw"), std::move(posList), RNBO::TAG(""));
        }
        if(CheckRNBOTag(*obj, "abs_up"))
        {
            auto posList = RNBO::make_unique<RNBO::list>();
            posList->push(param->absolute.up.x);
            posList->push(param->absolute.up.y);
            posList->push(param->absolute.up.z);
            obj->sendMessage(RNBO::TAG("abs_up"), std::move(posList), RNBO::TAG(""));
        }
    }



    FMOD_SPEAKERMODE GetSpeakermode(const RNBO::Index& channels)
    {
        switch(channels)
        {
            case 1:
                return FMOD_SPEAKERMODE_MONO;
                break;
            case 2:
                return FMOD_SPEAKERMODE_STEREO;
                break;
            case 4:
                return FMOD_SPEAKERMODE_QUAD;
                break;
            case 5:
                return FMOD_SPEAKERMODE_SURROUND;
                break;
            case 6:
                return FMOD_SPEAKERMODE_5POINT1;
                break;
            case 8:
                return FMOD_SPEAKERMODE_7POINT1;
                break;
            case 12:
                return FMOD_SPEAKERMODE_7POINT1POINT4;
                break;
            default:
                return FMOD_SPEAKERMODE_DEFAULT;
                break;
        }
    }

    bool CheckIfOutputQuiet(float* outarray,size_t buffsize, size_t numchans)
    {
        buffsize *= numchans;
        for (size_t i = 0; i< buffsize;i++)
        {
            if (abs(outarray[i]) > 1e-9)
                return false;
        }
        return true;
    }
}
