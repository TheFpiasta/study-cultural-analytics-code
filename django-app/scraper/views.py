from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, Http404
from django.template import loader

from scraper.models import ScrapeBatch


def index(request):
    latest_batch_list = ScrapeBatch.objects.order_by("created_at")[:5]
    # template = loader.get_template("scraper/index.html")
    context = {
        "latest_batch_list": latest_batch_list,
    }
    return render(request, "scraper/index.html", context)

def detail(request, batch_id):
    batch = ScrapeBatch.objects.get(pk=batch_id)
    print("#####" + str(batch))
    return render(request, "scraper/detail.html", {"question": batch})


def results(request, question_id):
    response = "You're looking at the results of batch %s."
    return HttpResponse(response % question_id)


def vote(request, question_id):
    return HttpResponse("You're voting on batch %s." % question_id)