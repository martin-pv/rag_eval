# BCG Pilot Review — Martin & Shirley

**Participants:** Martin, Shirley  
**Topic:** BCG product assessment, pilot options, gaps, and next steps for CVS IT review

> Note: Speaker labels are inferred from context (Martin prepared the deck; Shirley provided CVS IT feedback). ASR errors from the original recording are lightly cleaned for readability.

---

## Transcript

**Unknown:** Come here, Momo. Here.

**Shirley:** Hey, Martin.

**Martin:** Hey, Shirley, how are you? Hello. You're on mute?

**Shirley:** Are you— Shirley, how are you? Hey, good, good. How are you?

**Martin:** Sorry. Back-to-back call with Cy Morale and all these folks. All right.

**Shirley:** Okay. Do you want to go over the, what do you have now? Okay.

**Martin:** I put together a long book before—I just went and combined all of the information that I had and just reviewed the documentation that they provided. Okay, so I have a longer version and we can just keep as a record for this project in general, but also the presentation itself that we can present. Now, I made it a quick page longer and we can decide on how much we want to keep.

**Shirley:** Yeah, yeah. We can always shrink them.

**Martin:** Okay, and I didn't know if we, if there's a standard template. CVS?

**Shirley:** Yeah. There were, but it's okay.

**Martin:** I'm—I mean, this is more for the internal, for good.

**Shirley:** Okay. Great.

**Martin:** Okay. So basically, I wanted to break it down into 3 different things. So like what was presented? What are some of the gaps and then what should we do moving forward?

**Shirley:** Right? Excellent. Okay.

**Martin:** And give the recommendations right up front. So, basically, the idea is, basically deploy the product that BCG has into our environment, have it as a pilot, any other time before we even make a payment and then evaluate it, validate—because they have some certain strong claims. 80% on their auto recon rate—before actually migrating to phase two, which is the full deployment within—oh, actually, I think this got cut off a little bit. But the idea here is there's some risks, right?

So, the risks are contained from the beginning. Now, we sandbox the tenant, we keep it isolated, we can actually connect it. Well, initially they have a manual imports of documents.

**Shirley:** Yeah, okay.

**Martin:** And then there's no necessary financial commitment, but that's, I guess, all of this is dependent on the fact that we do the 2-part solution, the one of unpaid pilot, and then the rest of it goes through. I believe in one of the presentations I was looking at the transcript, they mentioned that this is gonna be a full handover to CVS. So I'm not sure exactly if that's going to be… What does that mean, right?

**Shirley:** Yeah, okay. What does that mean for handover? And they did not say a pay or something, right?

**Martin:** Right. And, yeah. Are they going to be, like, is it just a custom solution? They're completely gonna hand over the repo, hands off. We get the payments and it's done and over with. If that doesn't make any sense if we can't test the data and see everything that's up front.

Actually, evaluate it. Because even on the demo they have, there were some gaps already, where we saw there was an 80% promise for one of the metrics, for the auto recon rate, and the demo itself, actually, from the several runs that were created, it was showing 53. So you already see a gap right there, just from their own personal POC demo they were showing.

**Shirley:** Yeah, oh, okay.

**Martin:** Let me see if I have the… Yeah, I can pull this up later. We can go into the more in-depth one.

**Shirley:** Yeah, we can. Yeah, we can go, but this looks good. Looks good.

**Martin:** So these are the detailed detail pages, right? The one that we saw was like a high-level summary. What they delivered—

All right. Forecasts, but this is what they have. This is from their own demo, a screenshot, basically. And it was showing 53% when they were promising 80% auto reconciliation rate.

So, how is that gonna perform? Are we actually gonna reach 80%? If we don't reach 80%, I would, you know, we should refuse the payment for the next steps and not migrate to phase two. There's no point.

**Shirley:** Right, right.

**Martin:** There is one advantage to this, and I'm not sure if I should include it in the presentation as well—is because it's BCG, right? So they have a lot of experience with a lot of different clients. When I was working in McKinsey, we had access to just about everything from anywhere we can pull information from. So that's—there's an IP value to this. Because even if the code is relatively, let's say it's good, it's decent.

It's not very indoor. They still might have solutions of different things. Really one of them was a SQL agent engine, so basically replicating Snowflake's Cortex. The other one, they had some more customized, the different agents, because, you know, unless we have specialists in the field, those are gonna be a little bit more different. So if they already have them set up and they're specialized, this could be extremely useful.

**Shirley:** Yeah. Right, right.

**Martin:** It's, you know, they have a lot of clients and different exposure. So all kinds of, yeah. From variety, different industries, they compare, they've contrasted which one was the best, what's the best implementation?

So, the code itself might be transferable to different parts of our company or even just with us. If we get access to the code base, we have now a set of features to be able to pull through and utilize for any further projects in the future based on best practices supposedly.

That's all considering that… Assumed, yeah, exactly.

**Shirley:** Right, right. The assumption is coming from them, right? Company like this. Right? But we won't know until we see it, right?

**Martin:** No, and I think this gives us a little try. Now, whether or not we agree on this, because—and that's why I actually mentioned, I think we need to emphasize—is the sandbox tenant. So it's isolated from our environment. Keeps it safer for us.

But at the same time, they can have administrative rights, so we don't export the code out. But at the same time, we can still deploy our teams to be able to connect it to different services and be able to actually test it off. So I think this—

**Shirley:** Maybe let me, let's talk about that. I mean, I know you mentioned this sandbox tenant—like within CVS, or is this like the BCG owned?

**Martin:** So within CVS. So CVS under the same login and username, they can deploy just an empty environment. Second tenant. Just for this project specifically. Or it could be within our tenant as well. It doesn't have to be a second.

**Shirley:** Right, right. I mean, yeah, that's what I'm wondering—like, if it's, we already have our, not tenant per se. I don't think we're physically separated. It's more logical. We have our cluster. I would say. Yeah. Some way of isolating, giving them administrative rights for the code itself.

Well, why do we give them administrative rights? Think.

**Martin:** No, actually, it doesn't matter because you modify the code to bring it up to speed.

**Shirley:** Right, right. I mean, it's like, you're thinking is, we do minimum effort and let them—I mean, I can understand you—just let them build it in a way that business can do a true test.

**Martin:** Yes. Yeah, I guess not in that situation. Yeah, I mean, if it's a pilot too, we haven't purchased it. So maybe they don't want to necessarily put it in place where—

**Shirley:** Right, exactly. The code without pending payment. Right, right. I think that's where you come from. Is like, would they be willing to hand over the code for us to deploy to our system before paying and do a pilot. And if they don't, then what's the next thing is like maybe, like you said, a sandbox somewhere, allow business to use real data, certified, and then give them full access to deploy their code.

But yeah, I understand where you come from. That might just be the feasibility, knowing CVS—how flexible we are. If our company has to stand up this standalone tenant without deploying as it is and allowed to support our proprietary data, like PII.

I think that's a big ask. I mean, CVS has very strict—especially if we're talking about normal business documentations, you know, SOPs. It might not be a big deal, but as soon as we say like this headcount type of information, it might be—I believe it has PII, right? Did you read in the document? They say that, right?

**Martin:** Um, I would assume so if you're dealing with HR data.

**Shirley:** Yeah. Okay, I just don't know. Yeah, I just don't know at what level, if it's aggregated at like, you know, organization, you have 300 people. That may not be PII, but if they have individual—

**Martin:** I'll look into that. Yeah—is that the PII label? Let me pull up the demo as well.

So if we see the demo itself… Navigation, dashboard. No, I don't think… It's okay. It's probably not the individual level. It sounds like—oh, are those names L2? Did you have full names?

**Shirley:** Oh, that's PII. Full names are PII.

**Martin:** Yeah.

**Shirley:** And then if PII is involved, that'll be definitely something. I mean, from a CVS amount to use those information for the true information for testing might be a big concern, a big red flag.

And I suspect any sandbox, quote-unquote sandbox, it's gonna be certified in CVS—PII, it's very strict. Even in the production environment has to be protected, certified, and have all kinds of guardrails around it in terms of the hosting environment, access control, all of those things. Yeah, I worked with a vendor like a few years ago, we build our application on that platform. The assessment. It's very extensive. But take many months to even say allow.

So I'm thinking, yeah, I think maybe the more feasible thing—okay, we'll go through your assessment.

**Martin:** Yeah, I'll definitely add those more points in this one, like expand it out because it's true. If we're not gonna be going with a tenant, and just have it within our thing—every integration, every connection to it, we make it difficult even just deploying it on our side in any single way, it would have to be sometimes validating. Like you mentioned, access control and everything.

**Shirley:** Right. Yeah. I mean, those—that is sort of like the requirement, right? Like for us to be able to support a production PII data. We have to have like a proper access control. Those should not be a big, big change. We already actually have all the implementations of like access control in place. Deployment, we have our established CI/CD, we have the Kubernetes AD. You know, just like the boilerplate concept that Morali brought up. Oh, that's right.

Yeah, I mean, we could leverage a lot of the things that we built. Actually, yeah. So, okay. In that situation.

So we could bring up the sandbox and then we flag it, say this could be a compliance risk. We could face a lot of compliance roadblocks, all potential risk from a compliance perspective. You can mention that.

**Martin:** Yeah, definitely. I will note that. The other option is going with synthetic data that's, I guess, representative of our population. We can randomly sample some type of data that's real data and then see how it performs based on some of the reports that are already available from HR. And then basically, I think there's libraries out there that can go through that data and then we just create the synthetic data with the same distribution, same statistics, pretty much marrying that in for the same information, but with, I mean, obviously synthetic. Like a masked. I mean, we could mask all the PII, make it not expose. So that would be what that proposal is like—just use their current environment, right? Have business use that masked data, synthetic data to test, do parallel testing. That's another option, and the other option would be just—I mean, we can have all this. I mean, it's good to give options, right? Instead of just like, this is what you do. Okay, just one thing. I wanted to ask you about that actually. If you want me to put alternatives. So I'll add alternatives here too. Then in that case, for the presentation, would you like me to add that?

**Shirley:** Yeah, I mean, we can have the alternative. I'm gonna run by just the internal folks and to get some gauge before we talk to business. Okay. Make sure we're comfortable within IT before we present to the business. So let's throw the alternatives and then call out potential risk, like the pros and cons for each. Okay. And we get them options. Sounds good.

Yeah. And then I talked about basically all that—like you said, we already have this in theory, so that's not necessarily, so we can skip this one. And then the integration with all the different APIs because right now they're just manually importing data.

**Martin:** I'm not sure why they didn't offer—and they create this tool to basically be able to ingest data from APIs, which is a little bit strange that you have to manually export the data and then connect it.

**Shirley:** Yeah, that's too much work for external vendor to do outside of CVS. And obviously, they build this product. I mean, this is all the limitations. When we work with like BCG or, you know, KPMG and Deloitte. They always just build a silo product. I mean, even like one of the demo, I was included on the audit—internal audit—as KPMG built something, just standalone. It's not connecting to any of the data source. Connecting is a lot of work. That's why I kind of push it to phase two. Make sure we're certain this thing is valuable before we plug into our real data. And I think that's where you get the questions afterwards. Like, is that something—once we do the evaluation, decide, is that something that we want to take on? Does it have enough useful pipelines, useful agent orchestrations that are actually going to be sufficient enough for us to justify the cost. Or is this something that we can eventually build? If we can test it out that way somehow and do more, and we have to kind of make the decision down the line. But after the pilot—

**Martin:** And then just to clarify, because they did mention that it's gonna be fully transferable to us, and that they did design it to be transferable in general. So that actually is a big thing. The fact that it's transferable, meaning it's not going to be just within our team. We can roll it out to other places too, and modify it, and you actually use their pipeline for deployment. Let's say they have a Terraform pipeline to be able to deploy this over and have it standardized, maybe we can utilize some of those features the way they've done it. If it's some actual system that's designed really well to deploy without any issues.

**Shirley:** Yeah, I mean, if that's the case, absolutely. It's something that's—any of the features or foundations they have, our pipelines they build, can be leveraged, but again, like CVS actually has very—our preferred way, that's the thing. It's like last year, it took us a couple months to get our CI/CD, get GitHub Action–based CI/CD built. It's a lot of time—it's not up to us. It's like what is allowed, what are the tools of choice CVS has?

Yeah, from a CI/CD or DevOps perspective. Actually, CVS has—it's putting together this platform that allow sort of like a self-serve—it will build the CI/CD for you and allow you to pick and choose all the cards, you know, like you want the Postgres database, you want different Azure services. So you want a single sign-on. You can pick and choose and then you have them available immediately—something like that. This was very useful. So what you're describing sounds to me the way they have—what was it? CVS code?

**Martin:** CVS code, yeah.

**Shirley:** It's Cap. It's called Cap. Like, instead, we build—our team actually build our custom pipeline and go through that route. It's very difficult to actually—there was that up, it wasn't even there to support. But CVS now has this platform. And they started late last year and right now it's like rolling, expanding tomorrow, more scopes. So this pipeline deployment or even infrastructure provisioning becomes easier, supposedly if this platform ends up working properly. So I wouldn't worry too much about the deployment. I think even our current pipeline, we can easily leverage—through their front end and back end components and just—they have like a, I think blob storage. That's what I see using that. It's just setting up the connectors. They shouldn't be too big of an effort for us to stand this up.

**Martin:** Yeah I don't think so. And deploy it.

**Shirley:** Yeah, deploy it in our AKS community. I think that, as long if they are willing to go with that pilot option, handing over the source code, like you propose—we can deploy, and then business use, if they achieve their objective, 80%, like you said, then they can get to the payment option if there's a payment. Honestly, I don't even know how this engagement goes, whether business—I mean, they're buying it. I would imagine, who does things for free, right?

**Martin:** Yeah.

**Shirley:** That's unheard of. So if there's a payment and business, that's the preferred route, right? Business prefers—like if BCG agrees. We can go with that route. I think that's the ultimate test—how business use it, as if it's live in production. And the other way is like your alternative—have business mask the data. And then test it on their current environment. And then based on that, then decide on move forward to bring it in-house. And we will deploy.

I still want a first goal: live as it is in CVS. Because I still don't trust business will go all the way—spend too much time—because it's a lot of work to mask data. And then verification is not apple to apple. They have to translate the masked data to the real data to compare how well they perform. Knowing the business—they are not the ones that put too much work in testing. But they are okay to use it for real. So they basically want to have it working hands off, like they just bought it off the shelf somewhere and it works.

Yeah, knowing our business, that's how I would assume—I wouldn't expect them to do thorough, thorough testing, everything. They'll just probably do some basic—okay, I have this one set of data going through. Oh, everything looks good. Done, good. But in reality, for a true application—when business use it, it needs a period of time. Use it for different type of data, different scenarios, to even find out if this thing is robust enough. Not just a happy path scenario. Right?

So to me, I think either—have them hand over, we deploy in our CVS environment and have business use it for real. As a pilot, and then depends on the outcome—business need to set objective, right? What's the goal? Success criteria, KPIs. If they hit it then pay. That's the ideal situation, but if there's no agreement, then the next one is do the mask approach. Right? Tested on their environment—business need to do that, and in this case, I'm pretty sure they will just do some basic testing, do one set of testing—they will not spend 10 rounds or many rounds of testing, different scenarios.

I think in that case, like we'll do that, at least still have them do that. And then once they complete, we will take the product in, and we will deploy it into our production, as it is, and have business use it. And after we give them like several months, if they're happy, then we go to phase two, to do the integration. But that's what I would propose. Okay. Those are the two things. I mean, you have the sandbox—you can mention that, maybe put a caveat saying we can do that. We can delete the tenant part. It could be just any type of sandbox. Just as long as it's isolated.

**Martin:** Yeah, in a way. Right. I just see—we probably—that's the feasibility is unknown. I would put that caveat.

**Shirley:** First of all, if it's somewhere like a sandbox—the purpose is not to do the masked data, right? Synthetic data is going to be—real data. Right? And then real data, it has to be certified. For PII. Do you think the business or IT would want to go through the certification process? For a pilot? It's a long process. I don't know if it's worth to go through those months-long process just to get this product in. Honestly, that's a lot of effort. I mean, this guy said that they spent a few weeks to build this thing, and then we spent months just to get a certified sandbox—months out, maybe even longer. I don't know if it's even possible. Because CVS not only say you certify, then access control. You have to put all those bells and whistles almost like production grade. I just don't know if it's feasible, and then the other thing is—who owns that? And if we allow external vendor full access, that's another level of scrutiny. So, to me, that's the most difficult thing. I don't know if it's worth it for one single product, AI product like this. Given all those time, we would not build that product. And I think—oh, because they do have it currently deployed on their Azure platform, but that means absolutely no data can go with them, the real data. So the only thing that we can do would be the synthetic.

**Martin:** Yeah, that's the other option. Right? But synthetic—I think we should put the recommendation, its pros and cons. Pros will be: already available, we just need to do the testing. However, the con would be: no real data.

**Shirley:** No real data, right, right. No like connection we won't have. I want—yeah, because our option one is no live connection either. I don't want to do live—waste those time without knowing this thing works, right? So yeah, so for this synthetic data, it's like—it's still simulated testing. It may not catch all the scenarios. Real data—you know, real-ish scenarios. So there is a chance like it won't cover all the real test data scenarios. I think we'll just call this out and that's it. Give them those couple of options. And then we'll go from there. Okay, so—and in either case—

**Martin:** Sounds good?

**Shirley:** No, no, no. I would say either case—the first option, have them test for several months and then they can pay, and then depends on—at the end, if it meets the requirement and pay, then we go to the second phase to integrate. But if it's option 2, synthetic data testing, then our roadmap will be bringing it in to deploy as it is and have business use for some time. Then we'll do the integration because I'm fully expecting there's going to be issues, gaps, and business, and fixes, and change that—all this doesn't work. Or spend the time to get the product do what it's supposed to do, and then plug into the real data.

**Martin:** Okay. So I'll update that. Is there anything—besides adding those, the alternative and the pros and cons—do you want me to still leave a little bit of the features or is that too much to discuss, or end this as well? We can leave it there.

**Shirley:** These are fine. These are good. Yeah. We leave, I guess, as well.

**Martin:** Yeah. Okay. Oh, and then this—maybe I need to highlight this because this is what they claimed. So we wanna make sure.

**Shirley:** Okay, I think I see a split screen. Very tiny. Can you just—

**Martin:** Yeah, my monitors… The deck? Is that better?

**Shirley:** Mm. Yeah, better.

**Martin:** So, okay. I think this we need to highlight a little bit because this is what they claimed on the transcript. There's going to be a full—no subscription. So that would be potential.

**Shirley:** Right. No subscription. So you clarify at least.

**Martin:** Mm-hmm, okay. Yeah. Okay. And then I'll fix these ones, so it'll eliminate. I think the technical pretty much, mostly we're gonna drop out because of the thing about—I'll add the ones we discussed today. Okay. This could be also mentioned that necessarily it's going to be for phase two, so it doesn't really matter.

**Shirley:** Right, right. This—I think this whole page. Well, it's still worth to call out, though, integration. Because eventually we need—we have to get there. Right? The phase 2 will need to get there.

**Martin:** Okay. Yeah. Okay. Some revisions here, and then the next one, basically how to stabilize. Do we want to talk about the phase 2 and what, how we're gonna be stabilizing it, what we need to do in order to get it up to speed, the fact that we already have these pipelines available and we're just gonna use, or is that something—it's too much for this presentation?

**Shirley:** Well, let's see, so phase 2 is really stabilize and pilot, right? MicroCat, and prices as a secret, and operation.

**Martin:** Okay. Good, good. Yeah, we still have to build a pipeline, even we have it—we leverage whatever we have, or whatever they have, and we get it up and running. Yeah. Team Power Automate on Azure. They were talking about Teams / Power Automate, connection to Teams, to be able to communicate results. I'm actually don't know if they that much into the discussion. They briefly mentioned it here and there. Because this year, we send notifications directly. I guess something similar to the way already works here, right? It's—you have the ServiceNow, they can also integrate it with extra communication pathways, channels, Teams. And the fact that they can also—if they already have the connection to Power Automate, that gives a lot of automation capabilities to the business team, business users, because a lot of them know how to automate little things—maybe just get a report directly from Power Automate. They know how to do that. Not everyone, but some people. Less technical, but still capable.

**Shirley:** Okay, but you did mention validate those usage in CVS, right? It's not like we're committing to do and try. Validating, possibly. Is that what you meant? Validating?

**Martin:** There—marketing is one of the main features, so maybe we should validate it.

**Shirley:** Oh, is it? Okay. All right. Yeah, yeah, definitely. If it's a feature, we should. Integrate auto recon variance versus your benchmark. That's the 53%. Oh, investigate. Yeah, okay. Source code. Phase 2—is it work? API integration? Okay, good. So, scheduling. Okay—I think they were talking about different clouds. I'm not sure why… Sounds good. This is Disney—I need to take this out. Don't know why I keep saving you. Oh, okay. Risk assessment? Okay. It's updated. This is good. We're good.

I mean, I did kind of think like we initially—most likely will be on Azure because that's where we have all the existing, the most mature—require this work, and then later on we might migrate to GCP of the data. You know, Workday, and then plan, all those that are in GCP. So, and then the question, of course, so on the bottom, but we discussed these already for the most part. And then just—I think this is the only one we didn't touch upon is this one. Who's gonna own it finally? Are we—is it just going to be, because you need to have someone to be able to maintain it down the line. Is that something that we're gonna handle? Does IT handle any of that as well? Are we considered technically IT or we just—are we in the middleman right here?

**Shirley:** It's… IT—IT all, long term, IT, yeah.

**Martin:** I didn't hear what you said one more time.

**Shirley:** Yeah, IT will own the support, right? But business—

**Martin:** Yeah. And we're gonna help with the integration, correct? So we're the transition team.

**Shirley:** Okay. Business will own—it's a business application. IT will support. I think it's like that later.

**Martin:** Okay. Sorry—what were you saying?

**Shirley:** I was saying that we're basically just a transition team—the validation team and transition team, an integration team—to move it from the pilot over to the—

Possibly, yeah. I wouldn't think too much about this. This is… Maybe long-term—receipt based on with IT support, CVS IT support. That's it. But IT would not—when you say fully own all our applications, unless it's IT, like production support application, right? Business don't care. But it's a business function. Business own. Okay. IT support. Yeah. So you can just maybe remove those question marks and just say business own, with CVS IT support. That's it.

**Martin:** Yeah. Okay, we talk about this already, and then current state versus—I think this one we potentially—owners talk about it, like what's available, what's being done and what we're going to be substituting out, eventually for like phase 2 or phase one.

**Shirley:** Oh, I put—this should be phase 2 maybe. Yeah, current state migration… Target State is once—financing AI Azure platform. All these things. Okay? All right. And this is why with one of the option, we pilot option, we propose, right? So what does those T1, T2, T3s—are they target? Target one, two, three.

**Martin:** Oh, okay. The person Workday. Okay, all right, sounds good. So, I mean, this is a lot of information. Do you want me to keep all the slides?

**Shirley:** Yeah, we could keep it there. We just don't have to show them. Right? I think the most important thing is just to highlight, and then the proposal. And then we add the second alternative as well. Option one, two—yeah. So I'll add that. And then others will be there supporting. I always, like, when I create PowerPoint, I always have a lot in the appendix and then say, well, if they ask more questions, oh, I happen to have a slide here to talk about that. I have the full, actually. I just put together all the information I can pull out from anywhere. And even from the meetings. So I have—just a second, let me show you really quick. Okay. So we can go down. This is supposed to be an aggregate of all the information. So executive summary, what you've asked specifically what you wanted to talk about for this. What the POC is, everything that was able to extract out of the documents. So in case we need any extra clarification on anything, might have all the information that we can reference.

**Martin:** Okay. Yeah. So any type of more gaps, more technical gaps, integration gaps, and all that. So I just picked and choose the things most relevant to this. But yeah.

**Shirley:** And we can—if you want to, you're making some changes, right? You can send to me. If I have any other thoughts, I want to change something, I can tell you tomorrow morning. So I will just need this by—let me see—finalized by 10:30, before 10:30. Okay, so 10:30, before 10, just to be safe.

**Martin:** Yeah. Arizona 10—let's shoot for 10. To finalize. Yeah. How about all the discussions today? And oh—and then you said, let me know how your meeting goes with those other—I believe you said you had some insiders from the business thing that you wanted to discuss it before reaching out to the business, right? Or IT?

**Shirley:** Oh yeah, yeah. No, no, no. IT first, IT first, before business, right? I haven't arranged any business—and me, IT could very well have different opinions, but yeah, and tomorrow is the IT. I run with some of my IT leaders and then—if they—I need to bring them about everything—we had this meeting and see what they think, they want to move forward and should we take this on or not? All those things and then proposal is if they want to take on and these are what we propose. And get some feedback from them. And then we'll kind of formally propose. I may need to make some adjustments if we talk when we talk to business, if we do go forward with it.

**Martin:** Yeah. So I'll get these two for you tomorrow, and I'll also send you this as well. So just so you have it, all the information that's positive extracted so far. Sounds good.

**Shirley:** Yeah, you can drop it in Teams and I will take a look at today and if I have anything, I could drop you a message, send you an email and say, well, also make changes to this or some thoughts. Besides what we discussed.

**Martin:** Okay. Sounds a good plan.

**Shirley:** Okay. Alrighty. Great. Thanks a lot, Martin. Looks good. Thank you, thank you.

**Martin:** Thanks, thanks. All right, thank you. We'll talk to you later. Have a good one.

**Shirley:** You too, bye bye. Thanks. Bye.
