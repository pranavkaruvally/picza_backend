from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from chat.models import (
Post,
Comment,
Story
)

User = get_user_model()



class UserSerializer(serializers.ModelSerializer):

    

    def validate_password(self, value):
        print(self.initial_data)
        user = User.objects.create_user(email=self.initial_data['email'])
        validate_password(value,user)
        return value
    class Meta:

        model = User
        fields = ['email','password','uprn','username','token']
        extra_kwargs = {
            'password':{'write_only':True,},
            'uprn':{'required':True},
            'token':{'required':True},
            }

    # overriding the default create method. Because password is not encrypted in default create()
    def create(self,validated_data):
        
        user = User.objects.create_user(
                                            email=validated_data['email'],
                                            password=validated_data['password']
                                        )
        user.uprn = validated_data['uprn']
        user.username = validated_data['username']
        user.username_alias = validated_data['username']
        user.token = validated_data['token']
        user.save()
        return user

    def to_representation(self, instance):
        representation = super().to_representation(instance);
        representation['id'] = instance.id
        if self.context['type'] == 'login':
            representation['mood'] =  instance.profile.mood if instance.profile.mood else 0
            representation['general_last_seen'] = instance.profile.general_last_seen_off
            representation['last_seen_hidden'] = [user.username for user in instance.profile.yall_cant_see_me.all()]
            if(instance.dob is None):
                representation['dobVerified'] = False
            else:
                representation['dobVerified'] = True
                representation['dp'] = instance.profile.profile_pic.url if instance.profile.profile_pic else ''
        representation['f_name'] = instance.f_name if instance.f_name else ""
        representation['l_name'] = instance.l_name if instance.l_name  else ""
        return representation


class UserCustomSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['f_name','l_name','id']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        type = self.context['type']
        if type=="chat":
            representation['username'] = instance.username
        else:
            representation['username'] = instance.username_alias
        representation['dp'] = instance.profile.profile_pic.url if instance.profile.profile_pic else ''
        return representation


class UserRelatedField(serializers.RelatedField):

    def to_representation(self,instance):
        return {"f_name":instance.f_name,"l_name":instance.l_name,"id":instance.id,"username":instance.username_alias,"dp":instance.profile.profile_pic.url if instance.profile.profile_pic else ''}

    def get_queryset(self):
        return User.objects.all()

class PostSerializer(serializers.ModelSerializer):
    user = UserRelatedField()

    class Meta:

        model = Post
        fields = ["file","user",'id',"post_type",'caption']


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = self.context['user']
        representation['thumbnail'] = instance.thumbnail.url if instance.thumbnail else ''
        representation['comment_count']=instance.comment_set.all().count()
        if user in instance.likes.all():
            representation['hasLiked'] = True
        else:
            representation['hasLiked'] = False
        representation['likeCount'] = instance.likes.count()
        return representation


class PostRelatedField(serializers.RelatedField):

    def to_representation(self,instance):
      
        return {'id':instance.id,
                'url':instance.file.url,
                'likes':instance.likes.count(),
                'type':instance.post_type,
                'comments':instance.comment_set.all().count(),
                'thumbnail':instance.thumbnail.url if instance.thumbnail else ""}

    def get_queryset(self):
        return Post.objects.all()



class UserProfileSerializer(serializers.ModelSerializer):

    posts = PostRelatedField(many=True)

    class Meta:
        model = User
        fields = ["f_name","l_name","id","email","posts","about"]
        # depth = 1


    def to_representation(self,instance):
        representation = super().to_representation(instance)
        representation['username']=instance.username
        request = self.context['request']
        cur_user = self.context['cur_user']
        if(instance.profile.profile_pic):
            representation['dp']=instance.profile.profile_pic.url
        
        else:
            representation['dp']=''
        if instance==cur_user:
            representation['isMe'] = True
        else:
            representation['isMe'] = False
        print(request.count())
        representation['post_count'] = instance.posts.count()
        representation['friends_count'] = instance.profile.friends.count()
        if (request.count() == 1):
            if request.first().from_user==cur_user:
                if request.first().status == "accepted":
                    representation['requestStatus'] = "accepted"
                elif request.first().status == "pending":
                    representation['requestStatus'] = "pending"
                elif request.first().status == "rejected":
                    representation['requestStatus'] = "rejected"
            else:
                if request.first().status == "pending":
                    representation['requestStatus'] = "pending_acceptance"
                    representation['notif_id'] = request.first().id
                elif request.first().status == "accepted":
                    representation['requestStatus'] = "accepted"
                elif request.first().status == "rejected":
                    representation['requestStatus'] = "rejected"

        elif request.count()==0:
            if cur_user in instance.profile.friends.all():
                representation['requestStatus'] = "accepted"
            else:
                representation['requestStatus'] = "open"


        return representation


class CommentRelatedField(serializers.RelatedField):

    def to_representation(self,instance):
        return {'comment':instance.comment, 'dp':instance.user.profile.profile_pic.url, 'user':instance.user.username_alias}

    def get_queryset(self):
        return Comment.objects.all()

class PostDetailSerializer(serializers.ModelSerializer):

    comment_set = CommentRelatedField(many=True)

    class Meta:
        model = Post
        fields = ['file','caption','post_type','comment_set','id']

    def to_representation(self,instance):
        representation = super().to_representation(instance)
        representation ['thumbnail'] = instance.thumbnail.url if instance.thumbnail else ''
        user = self.context['user']
        representation['dp'] =  instance.user.profile.profile_pic.url if instance.user.profile.profile_pic else ''
        representation['username'] = instance.user.username_alias
        representation['user_id'] = instance.user.id
        representation['comment_count']=instance.comment_set.all().count()
        if user in instance.likes.all():
            representation['hasLiked'] = True
        else:
            representation['hasLiked'] = False
        representation['likeCount'] = instance.likes.count()
        like_dps = []
        if instance.likes.count()>0:
           
            if instance.likes.count()<=3:
                for user in instance.likes.all():
                    like_dps.append(user.profile.profile_pic.url)
            else:
                index = 1
                for user in instance.likes.all().reverse():
                    if index<=3:
                        like_dps.append(user.profile.profile_pic.url)
                        index+=1
                    else:
                        break
        representation['recent_likes'] = like_dps
        return representation



class StoryRelatedField(serializers.RelatedField):

    def to_representation(self, instance):
        return {"file":instance.file.url, "views":instance.views.count(),'time':instance.time_created.strftime("%Y-%m-%d %H:%M:%S")}

    def get_queryset(self):
        return Story.objects.all()


class UserStorySerializer(serializers.ModelSerializer):

    stories = StoryRelatedField(many=True)

    class Meta:
        model = User
        fields = ['username','id','stories']

    def to_representation(self,instance):
        if instance.stories.all().count()>0:
            representation = super().to_representation(instance)
            
            representation['dp'] = instance.profile.profile_pic.url if instance.profile.profile_pic else ''
            return representation
        else:
            return
