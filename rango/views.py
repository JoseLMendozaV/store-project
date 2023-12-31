from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from datetime import datetime

from rango.models import Category, Product, UserProfile, Article, Store, Wishlist
from rango.forms import CategoryForm, ProductForm, UserForm, UserProfileForm, ReviewForm, UserProfileEditForm, \
    ArticleForm, StoreForm
from rango.bing_search import run_query
from django.contrib import messages
import folium

class IndexView(View):
    def get(self, request):
        category_list = Category.objects.order_by('-name')[:5]
        product_list = Product.objects.order_by('-name')[:5]

        context_dict = {}

        context_dict['categories'] = category_list
        context_dict['products'] = product_list

        visitor_cookie_handler(request)

        response = render(request, 'rango/index.html', context=context_dict)
        return response


class AboutView(View):
    def get(self, request):
        context_dict = {}
        visitor_cookie_handler(request)
        context_dict['visits'] = request.session['visits']

        return render(request, 'rango/about.html', context=context_dict)


def search(request):
    result_list = []
    query = ''
    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            result_list_prov = Product.objects.all()

            for item in result_list_prov:

                if str(query).lower() in str(item).lower():
                    result_list.append(item)
                    print(item)
    print(result_list)

    return render(request, 'rango/search.html', {
        'result_list': result_list,
        'query': query
    })


class ShowCategoryView(View):
    def create_context_dict(self, category_name_slug):
        context_dict = {}
        try:
            category = Category.objects.get(slug=category_name_slug)
            products = Product.objects.filter(category=category).order_by('-name')

            context_dict['products'] = products
            context_dict['category'] = category
        except Category.DoesNotExist:
            context_dict['products'] = None
            context_dict['category'] = None

        return context_dict

    def get(self, request, category_name_slug):
        context_dict = self.create_context_dict(category_name_slug)
        return render(request, 'rango/category.html', context_dict)

    @method_decorator(login_required(login_url='/any/register/'))
    def post(self, request, category_name_slug):
        context_dict = self.create_context_dict(category_name_slug)
        query = request.POST['query'].strip()

        if query:
            context_dict['result_list'] = run_query(query)
            context_dict['query'] = query

        return render(request, 'rango/category.html', context_dict)


class AddCategoryView(View):
    @method_decorator(login_required(login_url='/any/register/'))
    def get(self, request):
        form = CategoryForm()
        return render(request, 'rango/add_category.html', {'form': form})

    @method_decorator(login_required(login_url='/any/register/'))
    def post(self, request):
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)
            return redirect(reverse('rango:index'))
        else:
            print(form.errors)

        return render(request, 'rango/add_category.html', {'form': form})


class ShowProductView(View):
    def get(self, request, slug):
        context_dict = {}

        try:
            product = Product.objects.get(slug=slug)

            context_dict['product'] = product

        except Product.DoesNotExist:
            context_dict['product'] = product

        #passes image path to read from static files
        context_dict['pathimg'] = "images/" + str(product.slug) + ".jpg"
        print("images/" + str(product.slug) + ".jpg")
        return render(request, 'rango/product.html', context=context_dict)


class AddProductView(View):
    def get_category_name(self, category_name_slug):
        try:
            category = Category.objects.get(slug=category_name_slug)
        except Category.DoesNotExist:
            category = None

        return category

    @method_decorator(login_required(login_url='/any/register/'))
    def get(self, request, category_name_slug):
        form = ProductForm()
        category = self.get_category_name(category_name_slug)

        if category is None:
            return redirect(reverse('rango:index'))

        context_dict = {'form': form, 'category': category}
        return render(request, 'rango/add_product.html', context_dict)

    @method_decorator(login_required(login_url='/any/register/'))
    def post(self, request, category_name_slug):
        form = ProductForm(request.POST)
        category = self.get_category_name(category_name_slug)

        if category is None:
            return redirect(reverse('rango:index'))

        if form.is_valid():
            if category:
                product = form.save(commit=False)
                product.category = category
                product.views = 0

                if 'picture' in request.FILES:
                    product.picture = request.FILES['picture']
                product.save()
                print(product)

                return redirect(reverse('rango:show_category',
                                        kwargs={'category_name_slug':
                                                    category_name_slug}))
        else:
            print(form.errors)

        context_dict = {'form': form, 'category': category}
        return render(request, 'rango/add_product.html', context=context_dict)


class ProfileView(View):
    @method_decorator(login_required(login_url='/any/register/'))
    def get(self, request):
        context_dict = {}
        try:
            profile = UserProfile.objects.get(user__username=request.user.username)

        except UserProfile.DoesNotExist:
            return render(request, 'rango/profile-with-OAuth.html')

        return render(request, 'rango/profile.html', {'profile': profile})

    @method_decorator(login_required(login_url='/any/register/'))
    def post(self, request):
        form = UserProfileEditForm(request.POST, instance=request.user)

        if form.is_valid():
            form.save(commit=True)
        else:
            print(form.errors)

        return render(request, 'rango/profile.html', context={'form': form})





@login_required(login_url='/any/register/')
def register_profile(request):
    form = UserProfileForm()

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES)

        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = request.user
            user_profile.save()

            return redirect(reverse('rango:index'))
        else:
            print(form.errors)

    context_dict = {'form': form}
    return render(request, 'rango/profile_registration.html', context_dict)


def register(request):
    registered = False
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user

            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
            profile.save()
            registered = True
        else:
            print(user_form.errors, profile_form.errors)
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render(request,
                  'rango/register.html',
                  context={'user_form': user_form,
                           'profile_form': profile_form,
                           'registered': registered})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user:
            if user.is_active:
                login(request, user)
                return redirect(reverse('rango:index'))
            else:
                return HttpResponse("Your Rango account is disabled.")
        else:
            print(f"Invalid login details: {username}, {password}")
            return HttpResponse("Invalid login details supplied.")
    else:
        return render(request, 'rango/login.html')


class AddReviewView(View):

    @method_decorator(login_required(login_url='/any/register/'))
    def get(self, request, slug):
        form = ReviewForm()
        product = Product.objects.get(slug=slug)

        if product is None:
            return redirect(reverse('rango:index'))

        context_dict = {'form': form, 'product': product}
        return render(request, 'rango/review.html', context=context_dict)

    def post(self, request, slug):
        form = ReviewForm(request.POST)
        product = Product.objects.get(slug=slug)

        if product is None:
            return redirect(reverse('rango:index'))
        if form.is_valid():
            if product:
                review = form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()

                return ShowProductView.get(ShowProductView, request, slug)
        else:
            print(form.errors)

        context_dict = {'form': form, 'product': product}
        return render(request, 'rango/review.html', context=context_dict)


@login_required(login_url='/any/register/')
def restricted(request):
    return render(request, 'rango/restricted.html')


@login_required(login_url='/any/register/')
def user_logout(request):
    logout(request)
    return redirect(reverse('rango:index'))


def get_server_side_cookie(request, cookie, default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val


def visitor_cookie_handler(request):
    visits = int(get_server_side_cookie(request, 'visits', '1'))
    last_visit_cookie = get_server_side_cookie(request,
                                               'last_visit',
                                               str(datetime.now()))
    last_visit_time = datetime.strptime(last_visit_cookie[:-7],
                                        '%Y-%m-%d %H:%M:%S')

    if (datetime.now() - last_visit_time).days > 0:
        visits = visits + 1
        request.session['last_visit'] = str(datetime.now())
    else:
        request.session['last_visit'] = last_visit_cookie

    request.session['visits'] = visits


@login_required(login_url='/any/register/')
def add_article(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            article_form = ArticleForm(request.POST, request.FILES)

            if article_form.is_valid():
                data = article_form.save(commit=False)
                data.author = request.user
                data.save()

                return redirect('/any/article/')   
            else:
                print(article_form.errors)
        else:
            form = ArticleForm()
        return render(request, 'rango/add_article.html', {'form': form})
    return redirect(reverse('rango:index'))


@login_required(login_url='/any/register/')
def edit_article(request, pk):
    if request.user.is_authenticated:

        article = Article.objects.get(id=pk)
        form = ArticleForm(instance=article)
        if request.user == article.author:
            if request.method == 'POST':
                form = ArticleForm(request.POST, request.FILES, instance=article)
                if form.is_valid():
                    form.save()

                    return redirect('/any/article/')

            context = {'form': form}

        else:
            messages.error(request, 'UPDATE NOT PERMITTED | The article belongs to another author.')
            return redirect('/any/article/')

    return render(request, 'rango/edit_article.html', context)


@login_required(login_url='/any/register/')
def delete_article(request, pk):
    if request.user.is_authenticated:
        article = Article.objects.get(id=pk)
        if request.user == article.author:
            if request.method == "POST":
                article.delete()
                return redirect('/any/article/')

            context = {'item': article}
        else:
            messages.error(request, 'DELETE NOT PERMITTED | The article belongs to another author.')
            return redirect('/any/article/')

    return render(request, 'rango/delete_article.html', context)


@login_required(login_url='/any/register/')
def article_show(request):
    if request.user.is_authenticated:
        article_list = Article.objects.all()
        context_dict = {}
        context_dict['articles'] = article_list

    return render(request, 'rango/article.html', context=context_dict)


def add_store(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            store_form = StoreForm(request.POST)

            if store_form.is_valid():
                data = store_form.save()
                data.save()
                return redirect(reverse('rango:index'))

        else:
            form = StoreForm()
        return render(request, 'rango/add_store.html', {'form': form})
    return redirect(reverse('rango:index'))


def store_show(request):
    context_dict = {}
    if request.user.is_authenticated:
        store_list = Store.objects.all()
        context_dict['stores'] = store_list

    return render(request, 'rango/store.html', context=context_dict)


@login_required(login_url='/any/register/')
def wishlist_view(request):
    products = Product.objects.filter(users_wishlist = request.user)
    context_dict = {"wishlist": products}
    return render(request, 'rango/wishlist_view.html', context_dict)
    
    
#    if request.method == 'GET':
#        product = request.GET.get('product')
#        print(product)
    # print(request)
    # wishlist = Wishlist.objects.all()
    # context_dict = {'wishlist': wishlist}
    # print(context_dict)
    # print(request.GET.get('product_id'))
    #
    # return render(request, 'rango/wishlist_view.html', context=context_dict)
#    return render(request, 'rango/wishlist_view.html', context={})

@login_required(login_url='/any/register/')
def add_wishlist_view(request, id):
    product = get_object_or_404(Product, id=id)
    
    if product.users_wishlist.filter(id=request.user.id).exists():
        product.users_wishlist.remove(request.user)
        messages.error(request, product.name + " has been removed from your WishList")
    else:
        product.users_wishlist.add(request.user)
        messages.success(request, "Added " + product.name + " to your WishList")
    return HttpResponseRedirect(request.META["HTTP_REFERER"])
        





def article_view(request):
    article_list = Article.objects.all()
    context_dict = {'articles': article_list}

    return render(request, 'rango/article_view.html', context=context_dict)


def article_information(request, pk):
    article = Article.objects.get(id=pk)

    context = {'article': article}

    return render(request, 'rango/article_information.html', context)








def store_information(request, pk):
    store = Store.objects.get(id=pk)

    m = folium.Map(location=[store.latitude, store.longitude], zoom_start=20)
    folium.Marker(
        [store.latitude, store.longitude],
        popup=store.name,
    ).add_to(m)
    m = m._repr_html_()


    return render(request, 'rango/store_information.html', {'store': store,'map': m})


# PAYPAL PAYMENT

import paypalrestsdk

paypalrestsdk.configure({
  "mode": "sandbox",  # "live" para producción
  "client_id": "ASccTIRrZCBVwlJLAtEGowdr4H7kgIvqI_7hFKJFN9HGtpIIUwApKR5oygkoy5ivdFM-WUfsKTLGq4ne",
  "client_secret": "EOMi1qZNHA5LlMBaDOBecOMN9C5URf_EiFeI86dGdTUcV-84nqYEZr5-8Spfh8Gb5HyaedB7oKbZVy_D"
})


from django.http import JsonResponse
from django.conf import settings
import paypalrestsdk

def create_payment(request):
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "http://localhost:8000/payment/execute/",
            "cancel_url": "http://localhost:8000/"},
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "Producto de prueba",
                    "sku": "sku",
                    "price": '5.00',
                    "currency": "USD",
                    "quantity": 1}]},
            "amount": {
                "total": '5.00',
                "currency": "USD"},
            "description": "Esta es la descripción del producto."}]})

    if payment.create():
        print("Payment created successfully")
    else:
        print(payment.error)

    return JsonResponse({"status": "success"})




def execute_payment(request):
    payment = paypalrestsdk.Payment.find("PAYMENT_ID_FROM_PAYPAL")

    if payment.execute({"payer_id": "PAYER_ID_FROM_PAYPAL"}):
        print("Payment execute successfully")
    else:
        print(payment.error)

    return JsonResponse({"status": "success"})
