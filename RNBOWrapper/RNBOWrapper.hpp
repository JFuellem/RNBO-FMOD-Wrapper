//
//  RNBOWrapper.hpp
//  RNBO_FMOD
//
//  Created by Jonas Füllemann on 19.01.24.
//

#ifndef RNBOWrapper_hpp
#define RNBOWrapper_hpp

#include <stdio.h>
#include <vector>

#include "RNBO.h"
#include "fmod.hpp"

#define MAX_CHANS 12

class RNBOWrapper
{
public:
    std::vector<std::unique_ptr<RNBO::CoreObject>> rnboObj;
    size_t isInstrument = 1;
    FMOD_BOOL inputsIdle = 0;
    FMOD_BOOL lastIdleState = 0;
    bool shouldGoIdle = false;
    size_t timeStore = 0;
    size_t tailLength = 0;
    int sampleRate = 48000;
    
    bool multiChannelExpandable;
    float* deInterleaveBuffer;
    float* interleaveBuffer;
    size_t lastChannelCount = -1;
    
    RNBOWrapper() : 
        deInterleaveBuffer(nullptr),
        interleaveBuffer(nullptr),
        lastChannelCount(-1),
        isInstrument(1),
        inputsIdle(0),
        lastIdleState(0),
        shouldGoIdle(false),
        timeStore(0),
        tailLength(0),
        sampleRate(48000),
        multiChannelExpandable(false)
    {}

    void Init();
    void Reset();

    ~RNBOWrapper() {
        if(deInterleaveBuffer) delete[] deInterleaveBuffer;
        if(interleaveBuffer) delete[] interleaveBuffer;
        rnboObj.clear();
    }
};

namespace RNBOFMODHelpers {

bool CheckRNBOTag(const RNBO::CoreObject &obj, const char* tag);

bool CheckAnyRNBOSystemTag(const RNBO::CoreObject &obj);

void DispatchRNBOMessages(RNBO::CoreObject *obj, void* rawData);

FMOD_SPEAKERMODE GetSpeakermode(const RNBO::Index& channels);
    
bool CheckIfOutputQuiet(float* outarray,size_t buffsize, size_t numchans);

}



#endif /* RNBOWrapper_hpp */
